{
    'name': 'Darakjian — Client Book',
    'summary': 'Support for the showroom selling process (Phase 1: the customer journey).',
    'description': """
Showroom selling support for Darakjian Jewelers.

Phase 1 — The customer journey. Provides:

- A 360° client book for the end customer.
- The client family as a first-class entity.
- A lead advisor assigned to each contact.
- A wishlist kept in sync between the website and the showroom.
- Holds and piece reservations with a configurable expiry.
- Appointment scheduling on the advisor's own calendar.
- An enriched piece record (4Cs, photos, video, uploaded certification).
- An in-house service workflow (repair, appraisal, traceable custody).
- Automatic attribution and commission for the advisor.

Design: data lives in the module's own tables, keyed to the native ones. No stored fields
are added to `res.partner`, `product.template` or `sale.order`. No dependencies on OCA,
ADHOC or any other third-party module.
""",
    'author': 'Yagüven C.G.',
    'maintainer': 'Yagüven C.G.',
    'website': 'https://github.com/Darakjian/yaguven_darakjian_client_book',
    'category': 'Sales/CRM',
    'version': '19.0.1.1.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'product',
        'stock',
        'sale_management',
        'calendar',
        'mail',
    ],
    'data': [
        'security/darakjian_security.xml',
        'security/ir.model.access.csv',
        'data/darakjian_sequences.xml',
        'data/darakjian_cron.xml',
        'data/rapaport_mock_data.xml',
        'views/menu.xml',
        'views/darakjian_appointment_views.xml',
        'views/darakjian_gem_card_views.xml',
        'views/darakjian_hold_views.xml',
        'views/darakjian_wishlist_views.xml',
        'views/darakjian_family_views.xml',
        'views/darakjian_salesperson_assignment_views.xml',
        'views/darakjian_service_ticket_views.xml',
        'views/darakjian_commission_views.xml',
        'wizards/darakjian_wizard_appointment_views.xml',
        'wizards/darakjian_wizard_hold_views.xml',
        'wizards/darakjian_wizard_service_intake_views.xml',
        'views/res_partner_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [
        'demo/darakjian_demo.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'yaguven_darakjian_client_book/static/src/scss/darakjian_post.scss',
        ],
    },
}
