from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import DarakjianTestCommon


@tagged('-at_install', 'post_install')
class TestDarakjianCommissionRule(DarakjianTestCommon):

    def test_single_open_rule_per_user(self):
        Rule = self.env['darakjian.commission.rule']
        Rule.create({
            'name': 'Rule A',
            'user_id': self.advisor.id,
            'percentage': 5.0,
            'valid_from': self._today(),
        })
        with self.assertRaises(ValidationError):
            Rule.create({
                'name': 'Rule B',
                'user_id': self.advisor.id,
                'percentage': 7.5,
                'valid_from': self._today(),
            })

    def test_close_rule_unblocks_creating_new_one(self):
        Rule = self.env['darakjian.commission.rule']
        first = Rule.create({
            'name': 'Rule A',
            'user_id': self.advisor.id,
            'percentage': 5.0,
            'valid_from': self._today(),
        })
        first.valid_to = self._today()
        second = Rule.create({
            'name': 'Rule B',
            'user_id': self.advisor.id,
            'percentage': 7.5,
            'valid_from': self._today(),
        })
        self.assertTrue(second.id, 'Should be able to open a new rule after closing the previous one')

    def test_percentage_bounds(self):
        Rule = self.env['darakjian.commission.rule']
        with self.assertRaises(ValidationError):
            Rule.create({
                'name': 'Negative',
                'user_id': self.advisor.id,
                'percentage': -5.0,
                'valid_from': self._today(),
            })
        with self.assertRaises(ValidationError):
            Rule.create({
                'name': 'Over 100',
                'user_id': self.advisor.id,
                'percentage': 120.0,
                'valid_from': self._today(),
            })


@tagged('-at_install', 'post_install')
class TestDarakjianCommissionLifecycle(DarakjianTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule = cls.env['darakjian.commission.rule'].create({
            'name': 'Test rule 10%',
            'user_id': cls.advisor.id,
            'percentage': 10.0,
            'valid_from': fields.Date.context_today(cls.env.user),
        })

    def _create_sale_order(self, price=1000.0):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.advisor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': price,
            })],
        })
        return order

    def test_create_from_sale_order_uses_active_rule(self):
        order = self._create_sale_order(price=5000.0)
        commission = self.env['darakjian.commission']._create_from_sale_order(order)
        self.assertTrue(commission)
        self.assertEqual(commission.rule_id, self.rule)
        self.assertAlmostEqual(commission.percentage, 10.0)
        self.assertAlmostEqual(commission.amount, order.amount_untaxed * 0.10, places=2)
        self.assertEqual(commission.state, 'calculated')

    def test_workflow_calculated_approved_paid(self):
        order = self._create_sale_order(price=3000.0)
        commission = self.env['darakjian.commission']._create_from_sale_order(order)
        commission.action_approve()
        self.assertEqual(commission.state, 'approved')
        self.assertEqual(commission.date_approved, self._today())
        commission.action_mark_paid()
        self.assertEqual(commission.state, 'paid')
        self.assertEqual(commission.date_paid, self._today())

    def test_cannot_cancel_paid_commission(self):
        order = self._create_sale_order(price=2000.0)
        commission = self.env['darakjian.commission']._create_from_sale_order(order)
        commission.action_approve()
        commission.action_mark_paid()
        with self.assertRaises(ValidationError):
            commission.action_cancel()
