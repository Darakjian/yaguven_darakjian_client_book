from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import DarakjianTestCommon


@tagged('-at_install', 'post_install')
class TestDarakjianFamily(DarakjianTestCommon):

    def test_single_primary_contact_per_family(self):
        family = self.env['darakjian.family'].create({'name': 'Test family'})
        self.env['darakjian.family.member'].create({
            'family_id': family.id,
            'partner_id': self.partner.id,
            'role': 'spouse',
            'is_primary_contact': True,
        })
        with self.assertRaises(ValidationError):
            self.env['darakjian.family.member'].create({
                'family_id': family.id,
                'partner_id': self.partner_other.id,
                'role': 'spouse',
                'is_primary_contact': True,
            })

    def test_primary_contact_compute(self):
        family = self.env['darakjian.family'].create({'name': 'Test family'})
        member = self.env['darakjian.family.member'].create({
            'family_id': family.id,
            'partner_id': self.partner.id,
            'role': 'spouse',
            'is_primary_contact': True,
        })
        self.assertEqual(family.primary_contact_partner_id, self.partner)
        member.is_primary_contact = False
        family.invalidate_recordset()
        self.assertFalse(family.primary_contact_partner_id)


@tagged('-at_install', 'post_install')
class TestDarakjianSalespersonAssignment(DarakjianTestCommon):

    def test_single_open_assignment_per_partner(self):
        Assignment = self.env['darakjian.salesperson.assignment']
        Assignment.create({
            'partner_id': self.partner.id,
            'user_id': self.advisor.id,
            'date_from': self._today(),
        })
        with self.assertRaises(ValidationError):
            Assignment.create({
                'partner_id': self.partner.id,
                'user_id': self.advisor.id,
                'date_from': self._today(),
            })

    def test_is_current_compute(self):
        Assignment = self.env['darakjian.salesperson.assignment']
        open_a = Assignment.create({
            'partner_id': self.partner.id,
            'user_id': self.advisor.id,
            'date_from': self._today(),
        })
        self.assertTrue(open_a.is_current)
        open_a.action_close()
        open_a.invalidate_recordset()
        self.assertFalse(open_a.is_current)


@tagged('-at_install', 'post_install')
class TestDarakjianWishlist(DarakjianTestCommon):

    def test_create_wishlist_assigns_default_name(self):
        wishlist = self.env['darakjian.wishlist'].create({
            'partner_id': self.partner.id,
            'salesperson_id': self.advisor.id,
        })
        self.assertTrue(wishlist.name)
        self.assertIn('Test Client', wishlist.name)

    def test_wishlist_line_unique_product(self):
        wishlist = self.env['darakjian.wishlist'].create({
            'partner_id': self.partner.id,
            'salesperson_id': self.advisor.id,
        })
        self.env['darakjian.wishlist.line'].create({
            'wishlist_id': wishlist.id,
            'product_id': self.product.id,
        })
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['darakjian.wishlist.line'].create({
                'wishlist_id': wishlist.id,
                'product_id': self.product.id,
            })
            self.env.cr.flush()

    def test_wishlist_workflow(self):
        wishlist = self.env['darakjian.wishlist'].create({
            'partner_id': self.partner.id,
            'salesperson_id': self.advisor.id,
        })
        self.assertEqual(wishlist.state, 'draft')
        wishlist.action_activate()
        self.assertEqual(wishlist.state, 'active')
        wishlist.action_archive_wishlist()
        self.assertEqual(wishlist.state, 'archived')
        wishlist.action_reset_to_draft()
        self.assertEqual(wishlist.state, 'draft')
