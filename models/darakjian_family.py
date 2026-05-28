from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DarakjianFamily(models.Model):
    _name = 'darakjian.family'
    _description = 'Darakjian — Family'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    notes = fields.Html()
    active = fields.Boolean(default=True, tracking=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    member_ids = fields.One2many(
        'darakjian.family.member',
        'family_id',
        string='Members',
    )
    member_count = fields.Integer(
        compute='_compute_member_count',
        store=False,
    )

    primary_contact_partner_id = fields.Many2one(
        'res.partner',
        compute='_compute_primary_contact_partner_id',
        store=True,
        string='Primary contact',
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)

    @api.depends('member_ids.is_primary_contact', 'member_ids.partner_id')
    def _compute_primary_contact_partner_id(self):
        for rec in self:
            primary = rec.member_ids.filtered(lambda m: m.is_primary_contact)[:1]
            rec.primary_contact_partner_id = primary.partner_id if primary else False

    def action_open_members(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members of %s') % self.name,
            'res_model': 'darakjian.family.member',
            'view_mode': 'list,form',
            'domain': [('family_id', '=', self.id)],
            'context': {'default_family_id': self.id},
        }


class DarakjianFamilyMember(models.Model):
    _name = 'darakjian.family.member'
    _description = 'Darakjian — Family member'
    _order = 'is_primary_contact desc, id asc'
    _check_company_auto = True

    family_id = fields.Many2one(
        'darakjian.family',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        domain="[('is_company', '=', False)]",
    )
    role = fields.Selection(
        [
            ('spouse', 'Spouse'),
            ('child', 'Child'),
            ('parent', 'Parent'),
            ('sibling', 'Sibling'),
            ('relative', 'Relative'),
            ('other', 'Other'),
        ],
        default='other',
        required=True,
    )
    is_primary_contact = fields.Boolean(
        string='Primary contact',
        help='Marks this member as the family primary contact. Only one per family.',
    )
    notes = fields.Text()

    company_id = fields.Many2one(
        related='family_id.company_id',
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            'family_partner_uniq',
            'unique(family_id, partner_id)',
            'A partner can only appear once in a given family.',
        ),
    ]

    @api.constrains('is_primary_contact', 'family_id')
    def _check_single_primary_contact(self):
        for rec in self:
            if not rec.is_primary_contact:
                continue
            others = self.search_count([
                ('family_id', '=', rec.family_id.id),
                ('is_primary_contact', '=', True),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(_(
                    'Family "%s" already has a primary contact. '
                    'Unset the existing one before assigning a new primary.'
                ) % rec.family_id.display_name)

    def name_get(self):
        result = []
        for rec in self:
            partner_name = rec.partner_id.display_name or ''
            family_name = rec.family_id.display_name or ''
            result.append((rec.id, f'{partner_name} ({family_name})'))
        return result
