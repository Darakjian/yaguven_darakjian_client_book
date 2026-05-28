from odoo.tests.common import tagged

from .common import DarakjianTestCommon


@tagged('-at_install', 'post_install')
class TestDarakjianGemCard(DarakjianTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure the Rapaport mock matrix is loaded before refresh tests run.
        cls.env['darakjian.rapaport.quote']._load_mock_matrix()

    def _create_diamond_card(self, carat=1.20, color='F', clarity='VS1'):
        return self.env['darakjian.gem.card'].create({
            'product_id': self.product.id,
            'kind': 'diamond',
            'four_cs_carat': carat,
            'four_cs_color': color,
            'four_cs_clarity': clarity,
            'four_cs_cut': 'excellent',
            'rapaport_source': 'mock',
        })

    def test_refresh_populates_rapaport_fields(self):
        card = self._create_diamond_card()
        self.assertFalse(card.rapaport_quote_id)
        self.assertEqual(card.rapaport_price_per_carat, 0)
        card.action_refresh_rapaport_price()
        self.assertTrue(card.rapaport_quote_id)
        self.assertGreater(card.rapaport_price_per_carat, 0)
        # ref price = price_per_carat × carat (1.20)
        self.assertAlmostEqual(
            card.rapaport_price_ref,
            card.rapaport_price_per_carat * 1.20,
            places=2,
        )
        self.assertTrue(card.rapaport_fetched_at)

    def test_refresh_skips_non_diamond_kinds(self):
        card = self.env['darakjian.gem.card'].create({
            'product_id': self.product.id,
            'kind': 'watch',
        })
        card.action_refresh_rapaport_price()
        self.assertFalse(card.rapaport_quote_id)
        self.assertEqual(card.rapaport_price_ref, 0.0)

    def test_refresh_skips_fancy_color(self):
        # Use a different product for the second card to avoid the
        # unique-product constraint on gem cards.
        another_template = self.env['product.template'].create({
            'name': 'Fancy yellow diamond piece',
            'type': 'consu',
        })
        card = self.env['darakjian.gem.card'].create({
            'product_id': another_template.product_variant_id.id,
            'kind': 'diamond',
            'four_cs_carat': 1.50,
            'four_cs_color': 'fancy',
            'four_cs_clarity': 'VS1',
        })
        card.action_refresh_rapaport_price()
        self.assertFalse(card.rapaport_quote_id,
                         'Fancy color should not be looked up against the standard matrix')

    def test_cron_refreshes_all_eligible_diamonds(self):
        card = self._create_diamond_card()
        self.env['darakjian.gem.card']._cron_refresh_rapaport_prices()
        card.invalidate_recordset()
        self.assertTrue(card.rapaport_quote_id)
        self.assertGreater(card.rapaport_price_ref, 0)
