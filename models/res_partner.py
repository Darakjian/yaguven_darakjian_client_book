from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    darakjian_titular_user_id = fields.Many2one(
        'res.users',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Titular advisor',
    )
    darakjian_family_ids = fields.Many2many(
        'darakjian.family',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Families',
    )
    darakjian_active_holds_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Active holds',
    )
    darakjian_appointments_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Appointments',
    )
    darakjian_appointment_next_id = fields.Many2one(
        'darakjian.appointment',
        compute='_compute_darakjian_client_book',
        store=False,
        string='Next appointment',
    )
    darakjian_wishlists_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Wishlists',
    )
    darakjian_service_tickets_open_count = fields.Integer(
        compute='_compute_darakjian_client_book',
        store=False,
        string='Open service tickets',
    )

    def _compute_darakjian_client_book(self):
        Assignment = self.env['darakjian.salesperson.assignment']
        Member = self.env['darakjian.family.member']
        Hold = self.env['darakjian.hold']
        Appointment = self.env['darakjian.appointment']
        Wishlist = self.env['darakjian.wishlist']
        Ticket = self.env['darakjian.service.ticket']
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()

        for rec in self:
            if not rec.id:
                rec.darakjian_titular_user_id = False
                rec.darakjian_family_ids = False
                rec.darakjian_active_holds_count = 0
                rec.darakjian_appointments_count = 0
                rec.darakjian_appointment_next_id = False
                rec.darakjian_wishlists_count = 0
                rec.darakjian_service_tickets_open_count = 0
                continue

            current_assignment = Assignment.search([
                ('partner_id', '=', rec.id),
                ('is_current', '=', True),
                ('active', '=', True),
            ], order='date_from desc', limit=1)
            rec.darakjian_titular_user_id = current_assignment.user_id

            members = Member.search([('partner_id', '=', rec.id)])
            rec.darakjian_family_ids = members.mapped('family_id')

            rec.darakjian_active_holds_count = Hold.search_count([
                ('partner_id', '=', rec.id),
                ('state', '=', 'active'),
            ])

            rec.darakjian_appointments_count = Appointment.search_count([
                ('partner_id', '=', rec.id),
            ])
            next_app = Appointment.search([
                ('partner_id', '=', rec.id),
                ('state', '=', 'confirmed'),
                ('datetime_start', '>=', now),
            ], order='datetime_start asc', limit=1)
            rec.darakjian_appointment_next_id = next_app

            rec.darakjian_wishlists_count = Wishlist.search_count([
                ('partner_id', '=', rec.id),
                ('active', '=', True),
            ])

            rec.darakjian_service_tickets_open_count = Ticket.search_count([
                ('partner_id', '=', rec.id),
                ('state', 'in', ('received', 'in_workshop', 'ready')),
            ])

    def action_open_darakjian_holds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Holds — %s') % self.display_name,
            'res_model': 'darakjian.hold',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_open_darakjian_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments — %s') % self.display_name,
            'res_model': 'darakjian.appointment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_open_darakjian_wishlists(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Wishlists — %s') % self.display_name,
            'res_model': 'darakjian.wishlist',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_open_darakjian_service_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Service tickets — %s') % self.display_name,
            'res_model': 'darakjian.service.ticket',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_open_darakjian_families(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Families — %s') % self.display_name,
            'res_model': 'darakjian.family',
            'view_mode': 'list,form',
            'domain': [('member_ids.partner_id', '=', self.id)],
        }

    def action_open_darakjian_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salesperson assignments — %s') % self.display_name,
            'res_model': 'darakjian.salesperson.assignment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
