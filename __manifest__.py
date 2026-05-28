{
    'name': 'Darakjian — Client Book',
    'summary': 'Acompañamiento al proceso de venta en showroom (Etapa 1: base del recorrido).',
    'description': """
Módulo de acompañamiento al proceso de venta para Darakjian Jewelers.

Etapa 1 — Base del recorrido. Provee:

- Client book 360° del cliente final.
- Familia cliente como entidad de primera clase.
- Asesor titular asignado a cada partner.
- Wishlist sincronizada sitio–showroom.
- Holds y reservas de pieza con expiración configurable.
- Agenda de cita integrada al calendario del asesor.
- Ficha de pieza enriquecida (4Cs, fotos, video, certificación cargada).
- Workflow de servicios in-house (reparación, valuación, custodia trazable).
- Atribución y comisión automática al asesor.

Diseño: datos en tablas propias del módulo con clave foránea a los nativos.
Sin campos almacenados sobre `res.partner`, `product.template` o `sale.order`.
Sin dependencias a OCA, ADHOC ni a otros módulos de terceros.
""",
    'author': 'Yagüven C.G.',
    'maintainer': 'Yagüven C.G.',
    'category': 'Sales/CRM',
    'version': '19.0.1.0.0',
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
