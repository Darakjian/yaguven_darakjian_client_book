from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    darakjian_commission_ids = fields.One2many(
        'darakjian.commission',
        'sale_order_id',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Commissions',
    )
    darakjian_commissions_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Commissions count',
    )
    darakjian_hold_ids = fields.One2many(
        'darakjian.hold',
        'sale_order_id',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Converted holds',
    )
    darakjian_holds_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Holds count',
    )

    def _compute_darakjian_client_book(self):
        Commission = self.env['darakjian.commission']
        Hold = self.env['darakjian.hold']
        for rec in self:
            if not rec.id:
                rec.darakjian_commission_ids = False
                rec.darakjian_commissions_count = 0
                rec.darakjian_hold_ids = False
                rec.darakjian_holds_count = 0
                continue
            commissions = Commission.search([('sale_order_id', '=', rec.id)])
            rec.darakjian_commission_ids = commissions
            rec.darakjian_commissions_count = len(commissions)
            holds = Hold.search([('sale_order_id', '=', rec.id)])
            rec.darakjian_hold_ids = holds
            rec.darakjian_holds_count = len(holds)

    def _action_confirm(self):
        result = super()._action_confirm()
        Commission = self.env['darakjian.commission']
        Hold = self.env['darakjian.hold']
        for order in self:
            Commission._create_from_sale_order(order)
            self._darakjian_convert_active_holds(order, Hold)
        return result

    @staticmethod
    def _darakjian_convert_active_holds(order, Hold):
        product_ids = order.order_line.mapped('product_id').ids
        if not product_ids:
            return
        active_holds = Hold.search([
            ('partner_id', '=', order.partner_id.id),
            ('product_id', 'in', product_ids),
            ('state', '=', 'active'),
        ])
        for hold in active_holds:
            hold.action_mark_converted(sale_order_id=order.id)

    def action_open_darakjian_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commissions — %s') % self.name,
            'res_model': 'darakjian.commission',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def action_open_darakjian_holds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Holds — %s') % self.name,
            'res_model': 'darakjian.hold',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
        }
