from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class DarakjianTestCommon(TransactionCase):
    """Shared fixtures for the Darakjian Client Book test suite.

    Builds the minimum graph of records every test in the suite needs:
    one client partner, one piece (product.product), one advisor user.
    Sub-tests extend this with model-specific records.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.advisor = cls.env.ref('base.user_admin')
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Client',
            'email': 'test.client@example.com',
        })
        cls.partner_other = cls.env['res.partner'].create({
            'name': 'Other Client',
            'email': 'other.client@example.com',
        })
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Piece — 1.00 ct F VS1',
            'type': 'consu',
            'sale_ok': True,
        })
        cls.product = cls.product_template.product_variant_id

    def _now(self):
        return fields.Datetime.now()

    def _today(self):
        return fields.Date.context_today(self.env.user)

    def _hours_later(self, hours):
        return self._now() + timedelta(hours=hours)

    def _days_later(self, days):
        return self._now() + timedelta(days=days)
