# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Management System',
    'version': '1.0.0',

    'summary': """
    Hotel management system is a system that provides us the ability to reserving rooms, 
    checking  whether the rooms are vacant are or not.""",

    'author': 'Serpent Consulting Services Pvt. Ltd., OpenERP SA, Mattobell LTD.',
    'category': 'Generic Modules/Hotel Management',
    'website': 'http://www.serpentcs.com',
    'depends': [
        'web',
        'base',
        'sale',
        'account_invoicing',
    ],
    'license': "AGPL-3",
    'demo': [
        'demo/hotel_room.xml',
        # 'views/hotel_data.xml',
    ],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_view.xml',
        # Tope 14/08/2018
        'data/ir_sequence.xml',
        'views/folio.xml',
        'views/hotel_room.xml',
        'views/product_product.xml',
        # data file
        'data/amenities.xml',
        # 'data/product_category.xml',
        # Tope 14/08/2018
        'views/hotel_sequence.xml',
        'views/hotel_report.xml',
        'views/report_hotel_management.xml',
        'wizard/hotel_checkin_checkout.xml',
        # 'wizard/hotel_wizard.xml',
        'views/action.xml',
        'views/menu.xml',
    ],
    'css': ['static/src/css/room_kanban.css'],
    'images': ['static/description/Hotel.png'],
    'auto_install': False,
    'installable': True,
    'application': True
}
