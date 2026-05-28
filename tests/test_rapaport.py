from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import DarakjianTestCommon


@tagged('-at_install', 'post_install')
class TestDarakjianRapaport(DarakjianTestCommon):

    def test_load_mock_matrix_populates_quotes(self):
        Quote = self.env['darakjian.rapaport.quote']
        before = Quote.search_count([('source', '=', 'mock')])
        Quote._load_mock_matrix()
        after = Quote.search_count([('source', '=', 'mock')])
        # The loader creates 5 bands × 4 colors × 4 clarities = 80 quotes.
        # When the data file already loaded them on install, the count
        # stays at 80 (idempotency); when starting empty, it grows by 80.
        self.assertGreaterEqual(after, 80)
        self.assertGreaterEqual(after, before)

    def test_load_mock_matrix_is_idempotent(self):
        Quote = self.env['darakjian.rapaport.quote']
        Quote._load_mock_matrix()
        first = Quote.search_count([('source', '=', 'mock')])
        created_second = Quote._load_mock_matrix()
        second = Quote.search_count([('source', '=', 'mock')])
        self.assertEqual(first, second)
        self.assertEqual(created_second, 0)

    def test_get_price_per_carat_finds_match(self):
        Quote = self.env['darakjian.rapaport.quote']
        Quote._load_mock_matrix()
        quote = Quote._get_price_per_carat(
            carat=1.20, color='F', clarity='VS1', source='mock',
        )
        self.assertTrue(quote, 'Expected a Rapaport quote match for 1.20 ct F VS1')
        # Base 14000 USD × color F (0.93) × clarity VS1 (0.75) = 9765
        self.assertAlmostEqual(quote.price_per_carat, 9765.0, places=2)

    def test_get_price_per_carat_no_match_outside_matrix(self):
        Quote = self.env['darakjian.rapaport.quote']
        Quote._load_mock_matrix()
        # The mock matrix only includes D/F/H/J colors; G is intentionally absent.
        quote = Quote._get_price_per_carat(
            carat=1.20, color='G', clarity='VS1', source='mock',
        )
        self.assertFalse(quote, 'Expected no match for an unsupported color')

    def test_carat_band_constraint(self):
        Quote = self.env['darakjian.rapaport.quote']
        usd = self.env.ref('base.USD')
        with self.assertRaises(ValidationError):
            Quote.create({
                'carat_min': 1.0,
                'carat_max': 0.5,
                'color': 'D',
                'clarity': 'IF',
                'price_per_carat': 1000.0,
                'currency_id': usd.id,
                'source': 'mock',
            })

    def test_price_per_carat_must_be_positive(self):
        Quote = self.env['darakjian.rapaport.quote']
        usd = self.env.ref('base.USD')
        with self.assertRaises(ValidationError):
            Quote.create({
                'carat_min': 0.5,
                'carat_max': 1.0,
                'color': 'D',
                'clarity': 'IF',
                'price_per_carat': 0.0,
                'currency_id': usd.id,
                'source': 'mock',
            })
