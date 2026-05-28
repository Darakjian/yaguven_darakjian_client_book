from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianWizardAppointment(models.TransientModel):
    """Quick scheduling of a showroom appointment from a partner form.

    Pre-fills the titular advisor and limits wishlist/hold pickers to the
    selected client. On confirm, creates a `darakjian.appointment` and
    optionally moves it straight to `confirmed` (which triggers the
    calendar.event creation by the appointment model itself).
    """

    _name = 'darakjian.wizard.appointment'
    _description = 'Darakjian — Schedule appointment wizard'

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    salesperson_id = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
    )
    datetime_start = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    duration_hours = fields.Float(
        required=True,
        default=1.0,
        help='Visit duration in hours. The end time is computed as '
             'start + duration when the appointment is created.',
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
    )
    wishlist_id = fields.Many2one(
        'darakjian.wishlist',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'active')]",
        help='Wishlist prepared for this visit. Limited to active '
             'wishlists of the selected client.',
    )
    hold_ids = fields.Many2many(
        'darakjian.hold',
        'darakjian_wizard_appointment_hold_rel',
        'wizard_id',
        'hold_id',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'active')]",
        string='Pieces on hold',
        help='Active holds to be brought out for this visit.',
    )
    notes_internal = fields.Html(
        string='Internal notes',
    )
    confirm_immediately = fields.Boolean(
        default=True,
        string='Confirm now',
        help='Confirm the appointment immediately, which also creates a '
             'calendar event for the advisor.',
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if not rec.partner_id:
                rec.wishlist_id = False
                rec.hold_ids = [(5, 0, 0)]
                continue
            if rec.partner_id.darakjian_titular_user_id:
                rec.salesperson_id = rec.partner_id.darakjian_titular_user_id
            # Reset to avoid stale values from a previous partner
            rec.wishlist_id = False
            rec.hold_ids = [(5, 0, 0)]

    def action_schedule(self):
        self.ensure_one()
        if self.duration_hours <= 0:
            raise ValidationError(_(
                'Duration must be greater than zero.'
            ))
        datetime_end = self.datetime_start + timedelta(hours=self.duration_hours)
        appointment = self.env['darakjian.appointment'].create({
            'partner_id': self.partner_id.id,
            'salesperson_id': self.salesperson_id.id,
            'datetime_start': self.datetime_start,
            'datetime_end': datetime_end,
            'kind': self.kind,
            'wishlist_id': self.wishlist_id.id if self.wishlist_id else False,
            'hold_ids': [(6, 0, self.hold_ids.ids)],
            'notes_internal': self.notes_internal or False,
        })
        if self.confirm_immediately:
            appointment.action_confirm()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment'),
            'res_model': 'darakjian.appointment',
            'res_id': appointment.id,
            'view_mode': 'form',
            'target': 'current',
        }
