from odoo import _, api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    darakjian_gem_card_id = fields.Many2one(
        'darakjian.gem.card',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Gem card',
    )
    darakjian_active_hold_id = fields.Many2one(
        'darakjian.hold',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Active hold',
    )
    darakjian_has_active_hold = fields.Boolean(
        compute='_compute_darakjian_client_book',
        store=False,
        string='On hold',
    )

    def _compute_darakjian_client_book(self):
        GemCard = self.env['darakjian.gem.card']
        Hold = self.env['darakjian.hold']
        for rec in self:
            if not rec.id:
                rec.darakjian_gem_card_id = False
                rec.darakjian_active_hold_id = False
                rec.darakjian_has_active_hold = False
                continue
            card = GemCard.search([('product_id', '=', rec.id)], limit=1)
            rec.darakjian_gem_card_id = card
            hold = Hold.search([
                ('product_id', '=', rec.id),
                ('state', '=', 'active'),
            ], limit=1)
            rec.darakjian_active_hold_id = hold
            rec.darakjian_has_active_hold = bool(hold)

    def action_open_or_create_gem_card(self):
        self.ensure_one()
        card = self.darakjian_gem_card_id
        if card:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Gem card'),
                'res_model': 'darakjian.gem.card',
                'res_id': card.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('New gem card'),
            'res_model': 'darakjian.gem.card',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_product_id': self.id},
        }

    def action_open_darakjian_active_hold(self):
        self.ensure_one()
        if not self.darakjian_active_hold_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active hold'),
            'res_model': 'darakjian.hold',
            'res_id': self.darakjian_active_hold_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductTemplate(models.Model):
    """Mirror Darakjian gem-card / hold info on the template form.

    For Darakjian's unique-piece jewelry, each template has exactly one
    variant. Templates therefore expose the variant's gem card and hold
    state as related fields so the smart buttons on the standard product
    form work without forcing the user to navigate to "Variants".
    """

    _inherit = 'product.template'

    darakjian_gem_card_id = fields.Many2one(
        'darakjian.gem.card',
        related='product_variant_id.darakjian_gem_card_id',
        readonly=True,
        string='Gem card',
    )
    darakjian_has_active_hold = fields.Boolean(
        related='product_variant_id.darakjian_has_active_hold',
        readonly=True,
    )

    def action_open_or_create_gem_card(self):
        self.ensure_one()
        variant = self.product_variant_id
        if not variant:
            return False
        return variant.action_open_or_create_gem_card()

    def action_open_darakjian_active_hold(self):
        self.ensure_one()
        variant = self.product_variant_id
        if not variant:
            return False
        return variant.action_open_darakjian_active_hold()
