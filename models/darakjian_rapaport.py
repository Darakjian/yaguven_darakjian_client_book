from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianRapaportQuote(models.Model):
    """Rapaport-style price quote for diamonds.

    Holds per-band quotes (carat range × color × clarity) and exposes a
    lookup with the public method `_get_price_per_carat`. Source is either
    `mock` (loaded from data/rapaport_mock_data.xml) or `live` (Phase 3,
    when Darakjian provides Rapaport API credentials). Call sites do not
    change between mock and live — only the `source` argument or the set
    of active records change.
    """

    _name = 'darakjian.rapaport.quote'
    _description = 'Darakjian — Rapaport price quote (mock or live)'
    _inherit = ['mail.thread']
    _order = 'valid_from desc, color, clarity, carat_min, id desc'
    _check_company_auto = True

    # ────────────────────────────────────────────────────────────────────
    # KEYS — carat band × color × clarity
    # ────────────────────────────────────────────────────────────────────
    carat_min = fields.Float(
        required=True,
        digits=(8, 3),
        tracking=True,
        help='Lower bound of the carat band (inclusive).',
    )
    carat_max = fields.Float(
        required=True,
        digits=(8, 3),
        tracking=True,
        help='Upper bound of the carat band (exclusive).',
    )
    color = fields.Selection(
        [
            ('D', 'D'), ('E', 'E'), ('F', 'F'),
            ('G', 'G'), ('H', 'H'), ('I', 'I'), ('J', 'J'),
            ('K', 'K'), ('L', 'L'), ('M', 'M'),
        ],
        required=True,
        tracking=True,
    )
    clarity = fields.Selection(
        [
            ('FL', 'FL'),
            ('IF', 'IF'),
            ('VVS1', 'VVS1'), ('VVS2', 'VVS2'),
            ('VS1', 'VS1'), ('VS2', 'VS2'),
            ('SI1', 'SI1'), ('SI2', 'SI2'),
            ('I1', 'I1'),
        ],
        required=True,
        tracking=True,
    )

    # ────────────────────────────────────────────────────────────────────
    # VALUE
    # ────────────────────────────────────────────────────────────────────
    price_per_carat = fields.Monetary(
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Reference price per carat. Multiplied by the actual carat '
             'weight at lookup time to obtain the piece reference price.',
    )

    # ────────────────────────────────────────────────────────────────────
    # METADATA
    # ────────────────────────────────────────────────────────────────────
    source = fields.Selection(
        [
            ('mock', 'Mock (simulated)'),
            ('live', 'Live (Rapaport API)'),
        ],
        required=True,
        default='mock',
        tracking=True,
        help='Mock quotes are loaded from module data for development and '
             'showroom training. Live quotes will be populated by the '
             'Rapaport API connector in Phase 3.',
    )
    valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    valid_to = fields.Date(
        help='Leave empty if this quote is still current.',
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        tracking=True,
        help='Leave empty to share this quote across all companies.',
    )

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )

    # ────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ────────────────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'band_color_clarity_source_uniq',
            'unique(carat_min, carat_max, color, clarity, source, valid_from, company_id)',
            'A Rapaport quote with the same band, color, clarity, source, '
            'start date and company already exists.',
        ),
    ]

    @api.constrains('carat_min', 'carat_max')
    def _check_carat_band(self):
        for rec in self:
            if rec.carat_min < 0:
                raise ValidationError(_(
                    'Carat band lower bound cannot be negative (got %s).'
                ) % rec.carat_min)
            if rec.carat_max <= rec.carat_min:
                raise ValidationError(_(
                    'Carat band upper bound (%s) must be strictly greater '
                    'than lower bound (%s).'
                ) % (rec.carat_max, rec.carat_min))

    @api.constrains('valid_from', 'valid_to')
    def _check_validity_range(self):
        for rec in self:
            if rec.valid_to and rec.valid_to < rec.valid_from:
                raise ValidationError(_(
                    'Quote end date (%s) cannot be earlier than start '
                    'date (%s).'
                ) % (rec.valid_to, rec.valid_from))

    @api.constrains('price_per_carat')
    def _check_price_positive(self):
        for rec in self:
            if rec.price_per_carat <= 0:
                raise ValidationError(_(
                    'Price per carat must be greater than zero.'
                ))

    @api.depends('carat_min', 'carat_max', 'color', 'clarity', 'source', 'valid_from')
    def _compute_name(self):
        for rec in self:
            label = '%.2f–%.2f ct · %s · %s · %s · %s' % (
                rec.carat_min or 0.0,
                rec.carat_max or 0.0,
                rec.color or '?',
                rec.clarity or '?',
                (rec.source or '?').upper(),
                rec.valid_from or '',
            )
            rec.name = label

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC LOOKUP API
    # ────────────────────────────────────────────────────────────────────
    @api.model
    def _get_price_per_carat(self, carat, color, clarity,
                             on_date=None, source='mock', company_id=None):
        """Return the quote record matching the requested combination.

        Args:
            carat: float, actual stone weight in carats.
            color: str, one of the GIA color codes (D..M).
            clarity: str, one of the GIA clarity codes (FL..I1).
            on_date: date, validity date. Defaults to today.
            source: 'mock' or 'live'.
            company_id: int or False, restrict to a company (False = shared).

        Returns:
            A `darakjian.rapaport.quote` recordset, limit=1. Empty if no
            band matches. Multiply `.price_per_carat * carat` at the call
            site to obtain the reference price.
        """
        if on_date is None:
            on_date = fields.Date.context_today(self)
        domain = [
            ('carat_min', '<=', carat),
            ('carat_max', '>', carat),
            ('color', '=', color),
            ('clarity', '=', clarity),
            ('source', '=', source),
            ('active', '=', True),
            ('valid_from', '<=', on_date),
            '|', ('valid_to', '=', False), ('valid_to', '>=', on_date),
        ]
        if company_id:
            domain += ['|',
                       ('company_id', '=', False),
                       ('company_id', '=', company_id)]
        return self.search(domain, limit=1)

    # ────────────────────────────────────────────────────────────────────
    # MOCK MATRIX LOADER — called once on install from data XML
    # ────────────────────────────────────────────────────────────────────
    @api.model
    def _load_mock_matrix(self):
        """Load the mock Rapaport matrix used in Phase 1.

        Idempotent: skips combinations already present for the same source
        and valid_from. Safe to invoke multiple times. Prices follow a
        plausible 2026-USD baseline scaled by color and clarity factors.

        Replace by the live Rapaport connector in Phase 3 — call sites
        keep using `_get_price_per_carat(...)`, no other code changes.
        """
        bands = [
            # (carat_min, carat_max, base USD per carat at D/IF)
            (0.50, 1.00, 8000.0),
            (1.00, 1.50, 14000.0),
            (1.50, 2.00, 18000.0),
            (2.00, 3.00, 25000.0),
            (3.00, 5.00, 32000.0),
        ]
        # GIA color factors (D = 1.00, descending)
        color_factors = {
            'D': 1.00,
            'F': 0.93,
            'H': 0.82,
            'J': 0.68,
        }
        # GIA clarity factors (IF = 1.00, descending)
        clarity_factors = {
            'IF': 1.00,
            'VVS1': 0.92,
            'VS1': 0.75,
            'SI1': 0.50,
        }
        valid_from = fields.Date.from_string('2026-01-01')
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        if not usd:
            return 0
        created = 0
        for carat_min, carat_max, base in bands:
            for color, cf in color_factors.items():
                for clarity, qf in clarity_factors.items():
                    ppc = round(base * cf * qf, 2)
                    exists = self.search_count([
                        ('carat_min', '=', carat_min),
                        ('carat_max', '=', carat_max),
                        ('color', '=', color),
                        ('clarity', '=', clarity),
                        ('source', '=', 'mock'),
                        ('valid_from', '=', valid_from),
                        ('company_id', '=', False),
                    ])
                    if exists:
                        continue
                    self.create({
                        'carat_min': carat_min,
                        'carat_max': carat_max,
                        'color': color,
                        'clarity': clarity,
                        'price_per_carat': ppc,
                        'source': 'mock',
                        'valid_from': valid_from,
                        'currency_id': usd.id,
                        'company_id': False,
                    })
                    created += 1
        return created
