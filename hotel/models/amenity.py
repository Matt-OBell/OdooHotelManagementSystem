"""."""
from odoo import api, fields, models


class Amenity(models.Model):
    """A hotel amenity is something of a premium nature 
    provided in addition to the room and its basics when renting a room at a 
    hotel."""

    _name = 'hotel.room.amenity'
    _description = 'Hotel amenity'

    name = fields.Char(string='Amenity', required=True)
    category_id = fields.Many2one('hotel.room.amenity.type',
                                  string='Type',
                                  required=False)


class AmenityCategory(models.Model):

    _name = 'hotel.room.amenity.type'
    _description = 'Amenities Category'

    name = fields.Char(string='Name')
