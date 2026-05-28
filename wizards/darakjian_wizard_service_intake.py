from odoo import _, api, fields, models


class DarakjianWizardServiceIntake(models.TransientModel):
    """Receive a piece in-house for service.

    Distinct from creating a `darakjian.service.ticket` directly because
    it enforces two things that the bare model cannot:
      - A photo of the piece at intake is required (audit evidence).
      - A custody location is required from the start (where the piece
        physically lives until handover).

    On submit, creates the ticket in state `received` and attaches the
    intake photo as the first custody evidence.
    """

    _name = 'darakjian.wizard.service.intake'
    _description = 'Darakjian — Service intake wizard'

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        help='Optional. Set when the piece exists in our catalog. '
             'Leave empty when the client brings something not in our '
             'inventory.',
    )
    piece_description = fields.Char(
        required=True,
        help='Free-text description of the piece received '
             '(e.g. "Vintage gold ring, ~5g, single round diamond").',
    )
    kind = fields.Selection(
        [
            ('reparation', 'Reparation'),
            ('appraisal', 'Appraisal'),
            ('custom_alteration', 'Custom alteration'),
            ('custody', 'Custody only'),
        ],
        default='reparation',
        required=True,
    )
    description = fields.Text(
        string='Client request',
        help='What the client asked for.',
    )

    date_received = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    date_promised = fields.Date()

    custody_location = fields.Char(
        required=True,
        help='Where the piece is physically kept '
             '(e.g. "Safe A, drawer 3").',
    )

    intake_photo = fields.Binary(
        required=True,
        attachment=True,
        string='Intake photo',
        help='Photo of the piece as received. Required as audit evidence.',
    )
    intake_photo_filename = fields.Char()

    received_by = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
    )
    assigned_to = fields.Many2one(
        'res.users',
        domain="[('share', '=', False)]",
        help='Optional. Workshop user assigned to the ticket.',
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id and not rec.piece_description:
                rec.piece_description = rec.product_id.display_name

    def action_create_ticket(self):
        self.ensure_one()
        ticket = self.env['darakjian.service.ticket'].create({
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id if self.product_id else False,
            'piece_description': self.piece_description,
            'kind': self.kind,
            'description': self.description or False,
            'date_received': self.date_received,
            'date_promised': self.date_promised or False,
            'custody_location': self.custody_location,
            'received_by': self.received_by.id,
            'assigned_to': self.assigned_to.id if self.assigned_to else False,
        })
        if self.intake_photo:
            attachment = self.env['ir.attachment'].create({
                'name': self.intake_photo_filename or _('Intake photo'),
                'datas': self.intake_photo,
                'res_model': 'darakjian.service.ticket',
                'res_id': ticket.id,
            })
            ticket.write({
                'custody_attachment_ids': [(4, attachment.id)],
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Service ticket'),
            'res_model': 'darakjian.service.ticket',
            'res_id': ticket.id,
            'view_mode': 'form',
            'target': 'current',
        }
