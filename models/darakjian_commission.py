from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianCommissionRule(models.Model):
    _name = 'darakjian.commission.rule'
    _description = 'Darakjian — Commission rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'user_id, valid_from desc, id desc'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users',
        required=True,
        index=True,
        domain="[('share', '=', False)]",
        tracking=True,
    )
    percentage = fields.Float(
        required=True,
        digits=(5, 2),
        help='Commission percentage applied to sale.order.amount_untaxed.',
        tracking=True,
    )
    min_margin = fields.Monetary(
        currency_field='currency_id',
        help='Minimum sale.order.amount_untaxed for the rule to apply. Acts as a floor, not a true margin.',
        tracking=True,
    )

    valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    valid_to = fields.Date(
        help='Leave empty if this rule is currently active.',
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )

    @api.constrains('valid_from', 'valid_to')
    def _check_validity_range(self):
        for rec in self:
            if rec.valid_to and rec.valid_to < rec.valid_from:
                raise ValidationError(_(
                    'Rule end date (%s) cannot be earlier than start date (%s).'
                ) % (rec.valid_to, rec.valid_from))

    @api.constrains('user_id', 'valid_to', 'active', 'company_id')
    def _check_single_open_rule_per_user(self):
        for rec in self:
            if not rec.active or rec.valid_to:
                continue
            others = self.search_count([
                ('user_id', '=', rec.user_id.id),
                ('company_id', '=', rec.company_id.id),
                ('valid_to', '=', False),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(_(
                    'User "%s" already has an open commission rule in company "%s". '
                    'Close the existing one (set valid_to) before creating a new one.'
                ) % (rec.user_id.name, rec.company_id.name))

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage < 0 or rec.percentage > 100:
                raise ValidationError(_('Percentage must be between 0 and 100.'))

    @api.model
    def _find_applicable(self, user_id, company_id, on_date, amount_untaxed):
        rules = self.search([
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
            ('active', '=', True),
            ('valid_from', '<=', on_date),
            '|', ('valid_to', '=', False), ('valid_to', '>=', on_date),
        ])
        return rules.filtered(lambda r: amount_untaxed >= r.min_margin)[:1]


class DarakjianCommission(models.Model):
    _name = 'darakjian.commission'
    _description = 'Darakjian — Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_calculated desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    sale_order_id = fields.Many2one(
        'sale.order',
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
    rule_id = fields.Many2one(
        'darakjian.commission.rule',
        ondelete='set null',
        tracking=True,
    )

    base_amount = fields.Monetary(
        currency_field='currency_id',
        help='Sale.order.amount_untaxed at the time of calculation.',
        tracking=True,
    )
    percentage = fields.Float(
        digits=(5, 2),
        tracking=True,
    )
    amount = fields.Monetary(
        currency_field='currency_id',
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('calculated', 'Calculated'),
            ('approved', 'Approved'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='calculated',
        required=True,
        tracking=True,
    )

    date_calculated = fields.Date(
        default=fields.Date.context_today,
        tracking=True,
    )
    date_approved = fields.Date(readonly=True, tracking=True)
    date_paid = fields.Date(readonly=True, tracking=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        store=True,
    )

    _sql_constraints = [
        (
            'sale_user_uniq',
            'unique(sale_order_id, user_id)',
            'A commission for this user on this sale order already exists.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('darakjian.commission')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.model
    def _create_from_sale_order(self, sale_order):
        if not sale_order:
            return self.browse()
        user = sale_order.user_id
        if not user:
            return self.browse()
        existing = self.search([
            ('sale_order_id', '=', sale_order.id),
            ('user_id', '=', user.id),
        ], limit=1)
        if existing:
            return existing
        rule = self.env['darakjian.commission.rule']._find_applicable(
            user_id=user.id,
            company_id=sale_order.company_id.id,
            on_date=sale_order.date_order.date() if sale_order.date_order else fields.Date.context_today(self),
            amount_untaxed=sale_order.amount_untaxed,
        )
        if not rule:
            return self.browse()
        amount = sale_order.amount_untaxed * rule.percentage / 100.0
        return self.create({
            'sale_order_id': sale_order.id,
            'user_id': user.id,
            'rule_id': rule.id,
            'base_amount': sale_order.amount_untaxed,
            'percentage': rule.percentage,
            'amount': amount,
            'company_id': sale_order.company_id.id,
        })

    def action_approve(self):
        for rec in self:
            if rec.state != 'calculated':
                raise ValidationError(_('Only calculated commissions can be approved.'))
            rec.state = 'approved'
            rec.date_approved = fields.Date.context_today(self)

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_('Only approved commissions can be marked as paid.'))
            rec.state = 'paid'
            rec.date_paid = fields.Date.context_today(self)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise ValidationError(_('Cannot cancel a paid commission.'))
            rec.state = 'cancelled'

    def action_recalculate(self):
        for rec in self:
            if rec.state not in ('calculated',):
                raise ValidationError(_('Only commissions in calculated state can be recalculated.'))
            rule = rec.rule_id or self.env['darakjian.commission.rule']._find_applicable(
                user_id=rec.user_id.id,
                company_id=rec.company_id.id,
                on_date=rec.date_calculated or fields.Date.context_today(self),
                amount_untaxed=rec.sale_order_id.amount_untaxed,
            )
            if not rule:
                raise ValidationError(_('No applicable commission rule found.'))
            rec.write({
                'rule_id': rule.id,
                'base_amount': rec.sale_order_id.amount_untaxed,
                'percentage': rule.percentage,
                'amount': rec.sale_order_id.amount_untaxed * rule.percentage / 100.0,
            })
