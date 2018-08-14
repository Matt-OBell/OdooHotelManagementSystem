# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Management System',
    'version': '0.0.1',

    'summary': """
    Hotel management system is a system that provides us the ability to reserving rooms, 
    checking  whether the rooms are vacant are or not.""",

    'author': 'Serpent Consulting Services Pvt. Ltd., OpenERP SA',
    'category': 'Generic Modules/Hotel Management',
    'website': 'http://www.serpentcs.com',
    'depends': [
        # 'sale_stock',
        # 'point_of_sale',
        'web'
    ],
    'license': "AGPL-3",
    'demo': ['views/hotel_data.xml'],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_sequence.xml',
        'views/hotel_report.xml',
        'views/report_hotel_management.xml',
        'views/hotel_view.xml',
        'wizard/hotel_wizard.xml',
    ],
    'css': ['static/src/css/room_kanban.css'],
    'images': ['static/description/Hotel.png'],
    'auto_install': False,
    'installable': True,
    'application': True
}
