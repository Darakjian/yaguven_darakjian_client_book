from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianHold(models.Model):
    _name = 'darakjian.hold'
    _description = 'Darakjian — Hold (piece reservation)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_expires asc, id desc'
    _check_company_auto = True

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    product_id = fields.Many2one(
        'product.product',
        required=True,
        index=True,
        ondelete='restrict',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        ondelete='restrict',
        tracking=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        required=True,
        index=True,
        domain="[('share', '=', False)]",
        default=lambda self: self.env.user,
        tracking=True,
    )

    date_start = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    date_expires = fields.Datetime(
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('converted', 'Converted to sale'),
            ('cancelled', 'Cancelled'),
        ],
        default='active',
        required=True,
        tracking=True,
    )
    notes = fields.Text()

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale order',
        readonly=True,
        copy=False,
        help='Sale order this hold was converted into.',
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('darakjian.hold')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.constrains('date_start', 'date_expires')
    def _check_date_range(self):
        for rec in self:
            if rec.date_expires <= rec.date_start:
                raise ValidationError(_(
                    'Hold expiration (%s) must be after the start date (%s).'
                ) % (rec.date_expires, rec.date_start))

    @api.constrains('product_id', 'state')
    def _check_single_active_hold_per_product(self):
        for rec in self:
            if rec.state != 'active':
                continue
            others = self.search_count([
                ('product_id', '=', rec.product_id.id),
                ('state', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(_(
                    'Product "%s" already has an active hold. '
                    'Cancel or convert the existing one before creating a new active hold.'
                ) % rec.product_id.display_name)

    def action_cancel(self):
        for rec in self:
            if rec.state in ('converted',):
                raise ValidationError(_('Cannot cancel a hold already converted to a sale.'))
            rec.state = 'cancelled'

    def action_extend(self, days=7):
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_('Only active holds can be extended.'))
            rec.date_expires = rec.date_expires + timedelta(days=days)

    def action_mark_converted(self, sale_order_id=False):
        for rec in self:
            if rec.state == 'converted':
                continue
            rec.state = 'converted'
            if sale_order_id:
                rec.sale_order_id = sale_order_id

    @api.model
    def _cron_expire_holds(self):
        now = fields.Datetime.now()
        due = self.search([
            ('state', '=', 'active'),
            ('date_expires', '<=', now),
        ])
        for rec in due:
            rec.state = 'expired'
        return len(due)

    @api.model
    def _cron_warn_expiring_holds(self, warn_within_days=2):
        now = fields.Datetime.now()
        threshold = now + timedelta(days=warn_within_days)
        upcoming = self.search([
            ('state', '=', 'active'),
            ('date_expires', '>', now),
            ('date_expires', '<=', threshold),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for rec in upcoming:
            existing = rec.activity_ids.filtered(
                lambda a: a.summary and 'Hold' in a.summary and a.user_id == rec.salesperson_id
            )
            if existing:
                continue
            rec.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                user_id=rec.salesperson_id.id,
                summary=_('Hold about to expire'),
                note=_(
                    'Hold %s for piece "%s" (client %s) expires on %s.'
                ) % (
                    rec.name, rec.product_id.display_name,
                    rec.partner_id.display_name, rec.date_expires,
                ),
                date_deadline=fields.Date.context_today(rec, rec.date_expires),
            )
        return len(upcoming)
