from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianSalespersonAssignment(models.Model):
    _name = 'darakjian.salesperson.assignment'
    _description = 'Darakjian — Salesperson assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, date_from desc, id desc'
    _check_company_auto = True

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        ondelete='restrict',
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        required=True,
        index=True,
        domain="[('share', '=', False)]",
        tracking=True,
    )
    date_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_to = fields.Date(
        help='Leave empty if this assignment is currently active.',
        tracking=True,
    )
    reason = fields.Text(
        help='Why the assignment was created or closed (e.g. "Reassigned due to vacations").',
    )
    active = fields.Boolean(default=True, tracking=True)
    is_current = fields.Boolean(
        compute='_compute_is_current',
        store=True,
        index=True,
        help='True when the assignment has no end date or end date is in the future.',
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    @api.depends('date_to')
    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_current = not rec.date_to or rec.date_to >= today

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_(
                    'Assignment end date (%s) cannot be earlier than start date (%s).'
                ) % (rec.date_to, rec.date_from))

    @api.constrains('partner_id', 'date_to', 'active')
    def _check_single_open_assignment(self):
        for rec in self:
            if not rec.active or rec.date_to:
                continue
            others = self.search_count([
                ('partner_id', '=', rec.partner_id.id),
                ('date_to', '=', False),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(_(
                    'Partner "%s" already has an open salesperson assignment. '
                    'Close the existing one (set its end date) before creating a new one.'
                ) % rec.partner_id.display_name)

    def action_close(self):
        for rec in self:
            if rec.date_to:
                continue
            rec.date_to = fields.Date.context_today(self)

    def name_get(self):
        result = []
        for rec in self:
            partner = rec.partner_id.display_name or ''
            user = rec.user_id.name or ''
            end = rec.date_to and f' → {rec.date_to}' or ' (current)'
            result.append((rec.id, f'{partner} · {user}{end}'))
        return result
