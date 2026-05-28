from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianWizardHold(models.TransientModel):
    """Place a piece on hold for a client with a configurable expiration.

    Designed to be opened either from a product form (piece in front of
    the client, advisor decides to reserve it) or from a partner form
    (client requests "keep that ring for me until Saturday").

    Surfaces any existing active hold on the same piece so the advisor
    sees the conflict before submitting, instead of hitting the
    `single_active_hold` constraint on save.
    """

    _name = 'darakjian.wizard.hold'
    _description = 'Darakjian — Place piece on hold wizard'

    product_id = fields.Many2one(
        'product.product',
        required=True,
        ondelete='cascade',
    )
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

    date_start = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    expiration_mode = fields.Selection(
        [
            ('days', 'After N days'),
            ('date', 'On a specific date'),
        ],
        default='days',
        required=True,
    )
    duration_days = fields.Integer(
        default=7,
        help='Used when expiration mode is "After N days".',
    )
    date_expires_explicit = fields.Datetime(
        string='Expires on',
        help='Used when expiration mode is "On a specific date".',
    )
    notes = fields.Text()

    existing_hold_id = fields.Many2one(
        'darakjian.hold',
        compute='_compute_existing_hold',
        readonly=True,
        help='Existing active hold on the same piece, if any. Must be '
             'cancelled or converted before a new hold can be created.',
    )
    existing_hold_warning = fields.Char(
        compute='_compute_existing_hold',
        readonly=True,
    )

    @api.depends('product_id')
    def _compute_existing_hold(self):
        Hold = self.env['darakjian.hold']
        for rec in self:
            if not rec.product_id:
                rec.existing_hold_id = False
                rec.existing_hold_warning = False
                continue
            existing = Hold.search([
                ('product_id', '=', rec.product_id.id),
                ('state', '=', 'active'),
            ], limit=1)
            rec.existing_hold_id = existing
            if existing:
                rec.existing_hold_warning = _(
                    'This piece is already on hold for %s until %s '
                    '(hold %s). Cancel that hold first if you need to '
                    'reassign the piece.'
                ) % (
                    existing.partner_id.display_name,
                    existing.date_expires,
                    existing.name,
                )
            else:
                rec.existing_hold_warning = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.darakjian_titular_user_id:
                rec.salesperson_id = rec.partner_id.darakjian_titular_user_id

    def _compute_date_expires(self):
        self.ensure_one()
        if self.expiration_mode == 'date':
            if not self.date_expires_explicit:
                raise ValidationError(_(
                    'You chose a specific date for expiration but no '
                    'date was provided.'
                ))
            if self.date_expires_explicit <= self.date_start:
                raise ValidationError(_(
                    'Expiration date (%s) must be after the start date (%s).'
                ) % (self.date_expires_explicit, self.date_start))
            return self.date_expires_explicit
        if self.duration_days <= 0:
            raise ValidationError(_(
                'Duration must be greater than zero days.'
            ))
        return self.date_start + timedelta(days=self.duration_days)

    def action_create_hold(self):
        self.ensure_one()
        if self.existing_hold_id:
            raise ValidationError(_(
                'Piece "%s" already has an active hold (%s) for "%s". '
                'Cancel or convert the existing hold before creating a '
                'new one.'
            ) % (
                self.product_id.display_name,
                self.existing_hold_id.name,
                self.existing_hold_id.partner_id.display_name,
            ))
        date_expires = self._compute_date_expires()
        hold = self.env['darakjian.hold'].create({
            'product_id': self.product_id.id,
            'partner_id': self.partner_id.id,
            'salesperson_id': self.salesperson_id.id,
            'date_start': self.date_start,
            'date_expires': date_expires,
            'notes': self.notes or False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hold'),
            'res_model': 'darakjian.hold',
            'res_id': hold.id,
            'view_mode': 'form',
            'target': 'current',
        }
