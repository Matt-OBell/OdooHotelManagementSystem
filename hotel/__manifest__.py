# See LICENSE file for full copyright and licensing details.
{
    'name': 'Hotel Management System',
    'version': '1.0.0',

    'summary': """
    Hotel management system is a system that provides us the ability to reserving rooms, 
    checking  whether the rooms are vacant are or not.""",

    'author': 'Mattobell LTD.',
    'category': 'Generic Modules/Hotel Management',
    'website': 'https://www.mattobell.com',
    'depends': [
        'web',
        'base',
        'sale',
        'account_invoicing',
    ],
    'license': "LGPL-3",
    'demo': [
        'demo/hotel_room.xml',
        'demo/amenities.xml',
    ],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_view.xml',
        'data/ir_sequence.xml',
        # Views
        'views/amenity.xml',
        'views/folio.xml',
        'views/hotel_room.xml',
        'views/product_product.xml',
        'views/hotel_sequence.xml',
        'views/hotel_report.xml',
        'views/report_hotel_management.xml',
        'wizard/hotel_checkin_checkout.xml',
        'wizard/hotel_wizard.xml',
        # Actions and Menu
        'views/action.xml',
        'views/menu.xml',
    ],
    'css': ['static/src/css/room_kanban.css'],
    'images': ['static/description/Hotel.png'],
    'auto_install': False,
    'installable': True,
    'application': False
}
