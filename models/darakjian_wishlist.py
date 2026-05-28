from odoo import _, api, fields, models


class DarakjianWishlist(models.Model):
    _name = 'darakjian.wishlist'
    _description = 'Darakjian — Wishlist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        ondelete='restrict',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('archived', 'Archived'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    source = fields.Selection(
        [
            ('web', 'Web'),
            ('showroom', 'Showroom'),
            ('advisor', 'Advisor'),
        ],
        default='showroom',
        required=True,
        tracking=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        domain="[('share', '=', False)]",
        tracking=True,
        help='Advisor who curates this wishlist with the client.',
    )
    notes = fields.Html()
    active = fields.Boolean(default=True, tracking=True)

    line_ids = fields.One2many(
        'darakjian.wishlist.line',
        'wishlist_id',
        string='Lines',
        copy=True,
    )
    line_count = fields.Integer(compute='_compute_line_count', store=False)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                vals['name'] = _('Wishlist of %s') % (partner.display_name or '?')
        return super().create(vals_list)

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_archive_wishlist(self):
        for rec in self:
            rec.state = 'archived'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'


class DarakjianWishlistLine(models.Model):
    _name = 'darakjian.wishlist.line'
    _description = 'Darakjian — Wishlist line'
    _order = 'priority desc, sequence asc, id asc'
    _check_company_auto = True

    wishlist_id = fields.Many2one(
        'darakjian.wishlist',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        'product.product',
        required=True,
        index=True,
    )
    notes = fields.Text()
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Normal'),
            ('2', 'High'),
        ],
        default='1',
        required=True,
    )
    is_fulfilled = fields.Boolean(
        help='Marked True when the client has purchased this item or when the advisor closes the line.',
    )

    company_id = fields.Many2one(
        related='wishlist_id.company_id',
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        related='wishlist_id.partner_id',
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            'wishlist_product_uniq',
            'unique(wishlist_id, product_id)',
            'A product can only appear once in a given wishlist.',
        ),
    ]
