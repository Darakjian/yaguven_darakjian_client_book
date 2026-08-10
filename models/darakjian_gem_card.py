from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools.misc import html_escape


class DarakjianGemCard(models.Model):
    _name = 'darakjian.gem.card'
    _description = 'Darakjian — Gem card (enriched product profile)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    product_id = fields.Many2one(
        'product.product',
        required=True,
        index=True,
        ondelete='cascade',
        tracking=True,
    )
    name = fields.Char(
        compute='_compute_name',
        store=True,
    )

    kind = fields.Selection(
        [
            ('diamond', 'Diamond'),
            ('colored_stone', 'Colored stone'),
            ('watch', 'Watch'),
            ('jewelry_piece', 'Jewelry piece'),
        ],
        required=True,
        default='diamond',
        tracking=True,
    )

    gia_report_number = fields.Char(tracking=True)
    igi_report_number = fields.Char(tracking=True)

    four_cs_carat = fields.Float(
        string='Carat',
        digits=(8, 3),
        tracking=True,
    )
    four_cs_color = fields.Selection(
        [
            ('D', 'D'), ('E', 'E'), ('F', 'F'),
            ('G', 'G'), ('H', 'H'), ('I', 'I'), ('J', 'J'),
            ('K', 'K'), ('L', 'L'), ('M', 'M'),
            ('N', 'N'), ('O_R', 'O–R'), ('S_Z', 'S–Z'),
            ('fancy', 'Fancy color'),
        ],
        string='Color',
        tracking=True,
    )
    four_cs_clarity = fields.Selection(
        [
            ('FL', 'FL'),
            ('IF', 'IF'),
            ('VVS1', 'VVS1'), ('VVS2', 'VVS2'),
            ('VS1', 'VS1'), ('VS2', 'VS2'),
            ('SI1', 'SI1'), ('SI2', 'SI2'),
            ('I1', 'I1'), ('I2', 'I2'), ('I3', 'I3'),
        ],
        string='Clarity',
        tracking=True,
    )
    four_cs_cut = fields.Selection(
        [
            ('excellent', 'Excellent'),
            ('very_good', 'Very Good'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Cut',
        tracking=True,
    )

    provenance_country_id = fields.Many2one(
        'res.country',
        string='Provenance country',
        tracking=True,
    )

    video_url = fields.Char(
        string='Video URL',
        help='Public or internal link to a 360° or multi-angle video of the piece.',
    )

    certification_pdf = fields.Binary(
        string='Certification PDF',
        attachment=True,
    )
    certification_pdf_filename = fields.Char(string='Certification filename')

    extra_photo_ids = fields.Many2many(
        'ir.attachment',
        'darakjian_gem_card_attachment_rel',
        'gem_card_id',
        'attachment_id',
        string='Extra photos',
        domain="[('mimetype', 'like', 'image/')]",
    )

    internal_notes = fields.Html()

    # ────────────────────────────────────────────────────────────────────
    # RAPAPORT REFERENCE PRICE (stub — replaced by live API in Phase 3)
    # ────────────────────────────────────────────────────────────────────
    rapaport_source = fields.Selection(
        [
            ('mock', 'Mock (simulated)'),
            ('live', 'Live (Rapaport API)'),
        ],
        default='mock',
        required=True,
        tracking=True,
        help='Source for the Rapaport reference price. Live becomes '
             'available in Phase 3 once Darakjian provides API credentials.',
    )
    rapaport_quote_id = fields.Many2one(
        'darakjian.rapaport.quote',
        string='Rapaport quote',
        readonly=True,
        ondelete='set null',
        copy=False,
        help='Last quote matched by the lookup. Kept for auditability.',
    )
    rapaport_price_per_carat = fields.Monetary(
        currency_field='currency_id',
        readonly=True,
        tracking=True,
        help='Snapshot of the price per carat at refresh time.',
    )
    rapaport_price_ref = fields.Monetary(
        currency_field='currency_id',
        readonly=True,
        tracking=True,
        help='Snapshot of price_per_carat × four_cs_carat at refresh time.',
    )
    rapaport_fetched_at = fields.Datetime(
        readonly=True,
        tracking=True,
        help='When the Rapaport reference was last refreshed for this card.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
        help='Currency for the Rapaport reference price snapshot.',
    )

    _sql_constraints = [
        (
            'product_uniq',
            'unique(product_id)',
            'A product can only have one gem card.',
        ),
    ]

    @api.depends('product_id', 'kind', 'gia_report_number')
    def _compute_name(self):
        for rec in self:
            base = rec.product_id.display_name or _('New gem card')
            if rec.gia_report_number:
                rec.name = f'{base} · GIA {rec.gia_report_number}'
            else:
                rec.name = base

    def action_open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product'),
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ────────────────────────────────────────────────────────────────────
    # RAPAPORT REFRESH
    # ────────────────────────────────────────────────────────────────────
    _NON_LOOKUP_COLORS = ('fancy', 'O_R', 'S_Z')

    def action_refresh_rapaport_price(self):
        """User-triggered refresh. Posts a chatter note when no match."""
        return self._refresh_rapaport_prices(post_no_match=True)

    @api.model
    def _cron_refresh_rapaport_prices(self):
        """Daily cron — silent refresh of all diamond cards.

        Skips colors that are not directly looked up against the standard
        Rapaport matrix (fancy, O-R, S-Z). For those, the price is set
        manually by the appraiser.
        """
        diamonds = self.search([
            ('kind', '=', 'diamond'),
            ('four_cs_carat', '>', 0),
            ('four_cs_color', 'not in', list(self._NON_LOOKUP_COLORS)),
            ('four_cs_color', '!=', False),
            ('four_cs_clarity', '!=', False),
        ])
        return diamonds._refresh_rapaport_prices(post_no_match=False)

    def _refresh_rapaport_prices(self, post_no_match=True):
        Quote = self.env['darakjian.rapaport.quote']
        updated = 0
        for rec in self:
            if rec.kind != 'diamond':
                continue
            if not (rec.four_cs_carat and rec.four_cs_color and rec.four_cs_clarity):
                continue
            if rec.four_cs_color in rec._NON_LOOKUP_COLORS:
                continue
            quote = Quote._get_price_per_carat(
                carat=rec.four_cs_carat,
                color=rec.four_cs_color,
                clarity=rec.four_cs_clarity,
                source=rec.rapaport_source or 'mock',
            )
            if not quote:
                if post_no_match:
                    body = (
                        '<p>%s</p>'
                        '<ul>'
                        '<li>%s: <strong>%s ct</strong></li>'
                        '<li>%s: <strong>%s</strong></li>'
                        '<li>%s: <strong>%s</strong></li>'
                        '<li>%s: <strong>%s</strong></li>'
                        '</ul>'
                    ) % (
                        html_escape(_('Rapaport refresh: no quote matched the 4Cs of this card.')),
                        html_escape(_('Carat')), html_escape(str(rec.four_cs_carat)),
                        html_escape(_('Color')), html_escape(rec.four_cs_color or ''),
                        html_escape(_('Clarity')), html_escape(rec.four_cs_clarity or ''),
                        html_escape(_('Source')), html_escape(rec.rapaport_source or 'mock'),
                    )
                    rec.message_post(
                        body=Markup(body),
                        subject=_('Rapaport refresh — no match'),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
                continue
            ppc = quote.price_per_carat
            rec.write({
                'rapaport_quote_id': quote.id,
                'rapaport_price_per_carat': ppc,
                'rapaport_price_ref': ppc * (rec.four_cs_carat or 0.0),
                'rapaport_fetched_at': fields.Datetime.now(),
                'currency_id': quote.currency_id.id,
            })
            updated += 1
        return updated
