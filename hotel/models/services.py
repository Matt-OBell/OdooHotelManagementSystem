"""."""
from odoo import api, fields, models


class HotelServices(models.Model):

    _name = 'hotel.services'
    _description = 'Hotel Services and its charges'

    # name = fields.Char(string='Name', required=True)
    product_id = fields.Many2one('product.product', ondelete='cascade',
                                 delegate=True, required=True)
    service_manager = fields.Many2one('res.users', string='Manager')

