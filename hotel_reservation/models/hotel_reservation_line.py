"""."""
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.exceptions import except_orm, ValidationError, UserError
import pytz


class HotelReservationLine(models.Model):

    _name = "hotel.reservation.line"
    _description = "Reservation Line"

    name = fields.Char('Name', size=64)
    line_id = fields.Many2one('hotel.reservation', string='Hotel')
    room_id = fields.Many2one('hotel.room')
    categ_id = fields.Many2one(related='room_id.categ_id', string='Category')
    capacity = fields.Integer(related='room_id.capacity', string='Capacity')


class HotelRoom(models.Model):

    _inherit = 'hotel.room'
    _description = 'Hotel Room'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ name_search(name='', args=None, operator='ilike', limit=100) -> records
        """
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not self._rec_name:
            _logger.warning(
                "Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        access_rights_uid = self._uid
        reserved_rooms_ids = self.env['hotel.reservation'].reserved_rooms_ids()
        print(reserved_rooms_ids)
        ids = self._search(args, limit=limit,
                           access_rights_uid=access_rights_uid)
        recs = self.browse(ids).filtered(
            lambda r: r.id not in reserved_rooms_ids and r.isavailable == True)
        return recs.sudo(access_rights_uid).name_get()
