from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianServiceTicket(models.Model):
    _name = 'darakjian.service.ticket'
    _description = 'Darakjian — In-house service ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_received desc, id desc'
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
    product_id = fields.Many2one(
        'product.product',
        string='Piece',
        index=True,
        ondelete='restrict',
        help='Optional product reference. Empty when the client brings a piece not in our catalog.',
    )
    piece_description = fields.Char(
        required=True,
        help='Free-text description of the piece received (e.g. "Vintage gold ring, ~5g, single round diamond").',
    )

    kind = fields.Selection(
        [
            ('reparation', 'Reparation'),
            ('appraisal', 'Appraisal'),
            ('custom_alteration', 'Custom alteration'),
            ('custody', 'Custody only'),
        ],
        required=True,
        default='reparation',
        tracking=True,
    )

    description = fields.Text(
        help='What the client requested.',
    )

    date_received = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_promised = fields.Date(tracking=True)
    date_delivered = fields.Date(readonly=True, tracking=True)

    state = fields.Selection(
        [
            ('received', 'Received'),
            ('in_workshop', 'In workshop'),
            ('ready', 'Ready for pickup'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ],
        default='received',
        required=True,
        tracking=True,
    )

    custody_location = fields.Char(
        help='Where the piece is physically kept (e.g. "Safe A, drawer 3").',
        tracking=True,
    )
    custody_attachment_ids = fields.Many2many(
        'ir.attachment',
        'darakjian_service_ticket_attachment_rel',
        'ticket_id',
        'attachment_id',
        string='Custody evidence',
        help='Photos and documents recorded during the custody flow (intake, workshop, handover).',
    )

    assigned_to = fields.Many2one(
        'res.users',
        domain="[('share', '=', False)]",
        tracking=True,
    )
    received_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        tracking=True,
        help='Advisor or staff member who received the piece.',
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
                seq = self.env['ir.sequence'].next_by_code('darakjian.service.ticket')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.constrains('date_received', 'date_promised')
    def _check_promised_after_received(self):
        for rec in self:
            if rec.date_promised and rec.date_promised < rec.date_received:
                raise ValidationError(_(
                    'Promised date (%s) cannot be earlier than received date (%s).'
                ) % (rec.date_promised, rec.date_received))

    def action_send_to_workshop(self):
        for rec in self:
            if rec.state != 'received':
                raise ValidationError(_('Only received tickets can be sent to workshop.'))
            rec.state = 'in_workshop'

    def action_mark_ready(self):
        for rec in self:
            if rec.state not in ('received', 'in_workshop'):
                raise ValidationError(_('Only received or in-workshop tickets can be marked ready.'))
            rec.state = 'ready'

    def action_deliver(self):
        for rec in self:
            if rec.state != 'ready':
                raise ValidationError(_('Only ready tickets can be delivered.'))
            rec.state = 'delivered'
            rec.date_delivered = fields.Date.context_today(self)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'delivered':
                raise ValidationError(_('Cannot cancel a delivered ticket.'))
            rec.state = 'cancelled'

    def action_reopen(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise ValidationError(_('Only cancelled tickets can be reopened.'))
            rec.state = 'received'
