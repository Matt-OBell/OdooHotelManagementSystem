import time
import datetime
from urllib.request import urlopen as urllib2
from odoo.exceptions import except_orm, ValidationError
from odoo.osv import expression
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _
from decimal import Decimal


ROOM_STATUS = [
    ('available', 'Available'),
    ('occupied', 'Occupied')
]


class HotelRoomType(models.Model):

    _name = "hotel.room.type"
    _description = "Room Type"

    status = fields.Boolean(string='Status')
    name = fields.Char('Name', required=True)
    base_occupant = fields.Integer(string='Base Occupant')
    room_ids = fields.Many2many('hotel.room', string='Rooms')
    extra_beds = fields.Integer(string='Extra Bed(s) Allowed')
    maximum_occupant = fields.Integer(string='Maximum Occupant')
    standard_price = fields.Float(string='Standard Price', required=True)


class HotelRoom(models.Model):

    _name = 'hotel.room'
    _description = 'Hotel Room'

    name = fields.Char(string='Name')
    floor_id = fields.Many2one('hotel.floor', string='Floor No')
    isavailable = fields.Boolean(
        string='Is Available', required=True, default=False)
    max_adult = fields.Integer('Max Adult')
    max_child = fields.Integer('Max Child')
    categ_id = fields.Many2one('hotel.room.type', string='Room Category',
                               required=True)
    amenities_ids = fields.Many2many('product.product', 'room_amenities',
                                     'rood_id', 'product_id',
                                     string='Room Amenities',
                                     help='List of room amenities.',
                                     domain=[('type', '=', 'amenity')])
    status = fields.Selection(selection=ROOM_STATUS,
                              string='Status', compute='_compute_status')
    capacity = fields.Integer(string='Capacity', required=True, default=1)
    product_manager = fields.Many2one('res.users', string='Product Manager')
    lease_price = fields.Float(string='Lease Price', required=True)
    total_price = fields.Float(
        string='Total Price', compute='_compute_total_price')

    @api.depends('isavailable')
    def _compute_status(self):
        for room in self:
            if room.isavailable:
                room.status = 'available'
            else:
                room.status = 'occupied'

    @api.multi
    def is_available(self):
        return self.status == 'available'

    @api.multi
    def preoccupy(self):
        return self.write({'isavailable': False})

    @api.depends('lease_price', 'categ_id')
    def _compute_total_price(self):
        for room in self:
            room.total_price = room.lease_price + room.categ_id.standard_price

    @api.constrains('capacity')
    def check_capacity(self):
        for room in self:
            if room.capacity <= 0:
                raise ValidationError(_('Room capacity must be more than 0'))

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if 'isavailable' in vals and vals['isavailable'] is False:
            vals.update({'color': 2, 'status': 'occupied'})
        if 'isavailable'in vals and vals['isavailable'] is True:
            vals.update({'color': 5, 'status': 'available'})
        ret_val = super(HotelRoom, self).write(vals)
        return ret_val

    @api.multi
    def set_room_status_occupied(self):
        """
        This method is used to change the state
        to occupied of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'isavailable': False, 'color': 2})

    @api.multi
    def set_room_status_available(self):
        """
        This method is used to change the state
        to available of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'isavailable': True, 'color': 5})
