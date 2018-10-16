# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.hotel.helper import decimal_to_time
from datetime import datetime, timedelta, date, time as tm


class HotelCheckinCheckout(models.TransientModel):
    _name = 'wizard.checkin.checkout'

    folio_id = fields.Many2one(comodel_name='hotel.folio', string='Folio')
    partner_id = fields.Many2one(
        omodel_name='res.partner',
        related='folio_id.partner_id',
        string='Partner'
    )
    number_of_days = fields.Integer(
        string='Number of Days', required=True, default=1)

    @api.multi
    def checkin(self):
        """When a user checkin, all the room on the folio will become unavailable
        till checkout time.
        """
        if self.folio_id.state != 'confirm':
            raise UserError(
                'This folio {} is not yet confirmed'.format(self.folio_id.name))
        hours, minutes = decimal_to_time(self.env.user.company_id.checkin_hour)
        can_check_in = datetime.combine(
            date.today(), tm(hours, minutes)) < datetime.now()
        if not can_check_in:
            raise UserError(
                'Guest(s) cannot be checked in earlier than {}'.format(
                    self.env.user.company_id.checkin_hour))
        for room in self.folio_id.room_ids:
            if room.is_available():
                room.preoccupy()
        self.folio_id.write({'state': 'checkin'})

    @api.multi
    def extend_stay(self):
        extend_from = fields.Datetime.from_string(self.folio_id.checkout_date)
        extend_to = timedelta(days=int(self.number_of_days))
        new_checkout_date = extend_from + extend_to
        self.folio_id.write({'checkout_date': new_checkout_date})

    def checkout(self):
        pass
