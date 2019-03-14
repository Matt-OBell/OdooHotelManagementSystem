import time
import datetime
from urllib.request import urlopen as urllib2
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _
from decimal import Decimal


ROOM_STATUS = [
    ('occupied', 'Occupied'),
    ('stayover', 'Stayover'),
    ('on_change', 'On-Change'),
    ('do_not_disturb', 'Do Not Disturb'),
    ('cleaning_in_progress', 'Cleaning in progress'),
    ('sleep_out', 'Sleep-out'),
    ('on_queue', 'On-Queue:'),
    ('skipper', 'Skipper'),
    ('vacant', 'Vacant'),
    ('out_of_order', 'Out of Order'),
    ('out_of_service', 'Out of Service'),
    ('lock_out', 'Lock out'),
    ('dnco', 'DNCO'),
    ('check-out', 'Check-Out'),
    ('late_check_out', 'Late Check out'),
]
ROOM_STATUS_HELP = """
    During the guest stay, the housekeeping status of the guest room changes 
    several times. The various terms defined are typical of the room status
    terminology of the lodging industry. Not every room status will occur
    for each and every guest during their stay at the hotel.

    Changes in this status should be promptly communicated to the front office
    in order to maximize the room sales and revenue. Maintaining timely 
    housekeeping status requires close coordination and cooperation
    between the front desk and the housekeeping department.

        Occupied: A guest is currently occupied in the room

        Stayover: The guest is not expected to check out today and will remain
        at least one more night.

        On-Change: The guest has departed, but the room has not yet been 
        cleaned and ready for sale.

        Do Not Disturb: The guest has requested not to be disturbed

        Cleaning in progress: Room attendant is currently cleaning this room.

        Sleep-out: A guest is registered to the room, but the bed has not been
        used.

        On-Queue: Guest has arrived at the hotel, but the room assigned is not 
        yet ready. In such cases, the room is put on Queue status in-order for
        the housekeeping staff to prioritise such rooms first.

        Skipper: The guest has left the hotel without making arrangements to 
        settle his or her account.

        Vacant and ready: The room has been cleaned and inspected and is ready
        for an arriving guest.

        Out of Order (OOO): Rooms kept under out of order are not sellable and
        these rooms are deducted from the hotel's inventory.A room may be 
        out-of-order for a variety of reasons, including the need of 
        maintenance, refurbishing and extensive cleaning etc.

        Out of Service (OOS ): Rooms kept under out of service are not deducted
        from the hotel inventory. This is a temporary blocking and reasons may
        be bulb fuse, T V remote not working, Kettle not working etc. 
        These rooms are not assigned to the guest once these small 
        maintenance issues are fixed.

        Lock out: The room has been locked so that the guest cannot re-enter 
        until he or she is cleared by a hotel official.

        DNCO ( did not check out): The guest made arrangements to settle his 
        or her bills ( and thus not a skipper), but has left without 
        informing the front desk.

        Due Out: The room is expected to become vacant after the following 
        guest checks out.

        Check-Out: The guest has settled his or her account, returned the room
         keys, and left the hotel.

        Late Check out: The guest has requested and is being allowed to check out 
        later than the normal / standard departure time of the hotel.
"""


class HotelRoomType(models.Model):

    _name = "hotel.room.type"
    _description = "Room Category"

    status = fields.Boolean(string='Status')
    name = fields.Char('Name', required=True)
    base_occupant = fields.Integer(string='Base Occupant')
    room_ids = fields.Many2many('hotel.room', string='Rooms')
    extra_beds = fields.Integer(string='Extra Bed(s) Allowed')
    maximum_occupant = fields.Integer(string='Maximum Occupant')
    standard_price = fields.Float(string='Standard Price', required=True)
    require_min_deposit = fields.Float(string='Required Deposits')


class HotelRoom(models.Model):

    _name = 'hotel.room'
    _description = 'Hotel Room'

    name = fields.Char(string='Name')
    floor_id = fields.Many2one('hotel.floor', string='Floor No')
    max_adult = fields.Integer('Max Adult')
    max_child = fields.Integer('Max Child')
    categ_id = fields.Many2one('hotel.room.type', string='Room Category',
                               required=True)
    amenities_ids = fields.Many2many('hotel.room.amenity', 'rel_room_id_amenity_id',
                                     string='Amenities',
                                     help='List of room amenities.')
    status = fields.Selection(selection=ROOM_STATUS,
                              string='Status',
                              help=ROOM_STATUS_HELP,
                              default='vacant')
    capacity = fields.Integer(string='Capacity', required=True, default=1)
    product_manager = fields.Many2one('res.users', string='Room Manager')
    lease_price = fields.Float(string='Extra Amenities', required=True)
    total_price = fields.Float(
        string='Total Price', compute='_compute_total_price')
    current_occupant = fields.Many2one('res.partner', string='Occupant')
    folio_ids = fields.One2many('hotel.folio', 'room_id', string='Folio')

    def check_room_status(self):
        pass

    @api.multi
    def isvacant(self):
        return self.status == 'vacant'

    @api.multi
    def occupy(self):
        return self.write({'status': 'occupied'})

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
    def set_room_status_occupied(self):
        """
        This method is used to change the state
        to occupied of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        # return self.write({'isavailable': False, 'color': 2})
        pass

    @api.multi
    def set_room_status_available(self):
        """
        This method is used to change the state
        to available of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        # return self.write({'isavailable': True, 'color': 5})
        pass
