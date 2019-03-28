# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Management - Base',
    'version': '11.0.1.0.0',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'category': 'Generic Modules/Hotel Management',
    'website': 'http://www.serpentcs.com',
    'depends': [
        'hotel',
        'board_frontdesk',
        'hotel_housekeeping',
        'hotel_pos_restaurant',
        'hotel_reservation',
        'hotel_restaurant',
        'report_hotel_reservation',
        'report_hotel_restaurant',
    ],
    'data': [
        # 'views/dashboard.xml' It man not be needed.
    ],
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': False,
    'application': True
}
