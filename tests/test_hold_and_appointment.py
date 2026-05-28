from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import DarakjianTestCommon


@tagged('-at_install', 'post_install')
class TestDarakjianHold(DarakjianTestCommon):

    def _create_hold(self, expires_in_days=7, partner=None, product=None):
        return self.env['darakjian.hold'].create({
            'product_id': (product or self.product).id,
            'partner_id': (partner or self.partner).id,
            'salesperson_id': self.advisor.id,
            'date_start': self._now(),
            'date_expires': self._days_later(expires_in_days),
        })

    def test_create_hold_assigns_sequence_name(self):
        hold = self._create_hold()
        self.assertTrue(hold.name.startswith('HOLD/'),
                        f'Unexpected hold name: {hold.name}')
        self.assertEqual(hold.state, 'active')

    def test_single_active_hold_per_product(self):
        self._create_hold()
        with self.assertRaises(ValidationError):
            self._create_hold(partner=self.partner_other)

    def test_can_create_hold_after_previous_cancelled(self):
        first = self._create_hold()
        first.action_cancel()
        # Same piece, different client — should now succeed.
        second = self._create_hold(partner=self.partner_other)
        self.assertEqual(second.state, 'active')

    def test_action_extend_pushes_expiration(self):
        hold = self._create_hold(expires_in_days=3)
        original = hold.date_expires
        hold.action_extend(days=5)
        self.assertEqual(hold.date_expires, original + timedelta(days=5))

    def test_cron_expire_holds_moves_due_to_expired(self):
        hold = self.env['darakjian.hold'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'salesperson_id': self.advisor.id,
            'date_start': self._now() - timedelta(days=10),
            'date_expires': self._now() - timedelta(days=1),
        })
        self.assertEqual(hold.state, 'active')
        self.env['darakjian.hold']._cron_expire_holds()
        hold.invalidate_recordset()
        self.assertEqual(hold.state, 'expired')


@tagged('-at_install', 'post_install')
class TestDarakjianAppointment(DarakjianTestCommon):

    def _create_appointment(self, salesperson=None, start_hours=1, duration_hours=1):
        return self.env['darakjian.appointment'].create({
            'partner_id': self.partner.id,
            'salesperson_id': (salesperson or self.advisor).id,
            'datetime_start': self._hours_later(start_hours),
            'datetime_end': self._hours_later(start_hours + duration_hours),
        })

    def test_create_appointment_assigns_sequence_name(self):
        appointment = self._create_appointment()
        self.assertTrue(appointment.name.startswith('APT/'),
                        f'Unexpected appointment name: {appointment.name}')
        self.assertEqual(appointment.state, 'draft')

    def test_end_must_be_after_start(self):
        with self.assertRaises(ValidationError):
            self.env['darakjian.appointment'].create({
                'partner_id': self.partner.id,
                'salesperson_id': self.advisor.id,
                'datetime_start': self._hours_later(2),
                'datetime_end': self._hours_later(1),
            })

    def test_action_confirm_creates_calendar_event(self):
        appointment = self._create_appointment()
        self.assertFalse(appointment.event_id)
        appointment.action_confirm()
        self.assertEqual(appointment.state, 'confirmed')
        self.assertTrue(appointment.event_id,
                        'Confirming should have created a linked calendar event')

    def test_no_overlap_for_same_salesperson(self):
        first = self._create_appointment(start_hours=2, duration_hours=2)
        first.action_confirm()
        second = self._create_appointment(start_hours=3, duration_hours=2)
        with self.assertRaises(ValidationError):
            second.action_confirm()

    def test_action_cancel_clears_calendar_event(self):
        appointment = self._create_appointment()
        appointment.action_confirm()
        event = appointment.event_id
        appointment.action_cancel()
        self.assertEqual(appointment.state, 'cancelled')
        # Native Odoo "archive" semantics: the event becomes inactive
        # but the FK is kept for traceability.
        self.assertFalse(event.active)
