from odoo import api, fields, models


class ReservationLine(models.Model):
    """docstring for reservation line"""

    _name = 'hotel.reservation.line'

    room_id = fields.Many2one('hotel.room', string='Room')
    arrival = fields.Datetime(string='Arrival', required=True)
    departure = fields.Datetime(string='Departure', required=True)
    adults = fields.Integer(string='Adults', default=1,
                            help='List of adults there in guest list. ')
    children = fields.Integer(
        string='Children', default=0, help='Number of children there in guest list.')
    reservation_id = fields.Many2one('hotel.reservation', string='Reservation')
