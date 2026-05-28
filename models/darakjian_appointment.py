from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianAppointment(models.Model):
    _name = 'darakjian.appointment'
    _description = 'Darakjian — Showroom appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'datetime_start desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
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

    datetime_start = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    datetime_end = fields.Datetime(
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('no_show', 'No show'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )

    kind = fields.Selection(
        [
            ('walk_in', 'Walk-in'),
            ('scheduled', 'Scheduled'),
            ('bridal_consult', 'Bridal consult'),
            ('watch_appointment', 'Watch appointment'),
        ],
        default='scheduled',
        required=True,
        tracking=True,
    )

    wishlist_id = fields.Many2one(
        'darakjian.wishlist',
        domain="[('partner_id', '=', partner_id)]",
        help='Wishlist prepared for this appointment.',
    )
    hold_ids = fields.Many2many(
        'darakjian.hold',
        'darakjian_appointment_hold_rel',
        'appointment_id',
        'hold_id',
        string='Related holds',
    )
    event_id = fields.Many2one(
        'calendar.event',
        string='Calendar event',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    notes_internal = fields.Html(string='Internal notes')

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
                seq = self.env['ir.sequence'].next_by_code('darakjian.appointment')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.constrains('datetime_start', 'datetime_end')
    def _check_date_range(self):
        for rec in self:
            if rec.datetime_end <= rec.datetime_start:
                raise ValidationError(_(
                    'Appointment end (%s) must be after the start (%s).'
                ) % (rec.datetime_end, rec.datetime_start))

    @api.constrains('salesperson_id', 'datetime_start', 'datetime_end', 'state')
    def _check_no_overlap_for_salesperson(self):
        for rec in self:
            if rec.state not in ('confirmed',):
                continue
            overlap = self.search_count([
                ('id', '!=', rec.id),
                ('salesperson_id', '=', rec.salesperson_id.id),
                ('state', '=', 'confirmed'),
                ('datetime_start', '<', rec.datetime_end),
                ('datetime_end', '>', rec.datetime_start),
            ])
            if overlap:
                raise ValidationError(_(
                    'Advisor "%s" already has a confirmed appointment overlapping this time slot.'
                ) % rec.salesperson_id.name)

    def _build_calendar_event_vals(self):
        self.ensure_one()
        return {
            'name': _('Darakjian appointment — %s') % (self.partner_id.display_name or ''),
            'start': self.datetime_start,
            'stop': self.datetime_end,
            'user_id': self.salesperson_id.id,
            'partner_ids': [(6, 0, [self.partner_id.id, self.salesperson_id.partner_id.id])],
            'description': self.notes_internal or '',
        }

    def action_confirm(self):
        for rec in self:
            if rec.state == 'confirmed':
                continue
            if rec.state in ('done', 'cancelled', 'no_show'):
                raise ValidationError(_(
                    'Cannot confirm an appointment in state %s.'
                ) % dict(rec._fields['state'].selection).get(rec.state))
            if not rec.event_id:
                event = self.env['calendar.event'].create(rec._build_calendar_event_vals())
                rec.event_id = event.id
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            rec.state = 'cancelled'
            if rec.event_id:
                rec.event_id.active = False

    def action_mark_done(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise ValidationError(_('Only confirmed appointments can be marked as done.'))
            rec.state = 'done'

    def action_mark_no_show(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise ValidationError(_('Only confirmed appointments can be marked as no-show.'))
            rec.state = 'no_show'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            if rec.event_id:
                rec.event_id.active = False
                rec.event_id = False
