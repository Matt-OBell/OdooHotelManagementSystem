# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HotelCheckinCheckout(models.TransientModel):
    _name = 'wizard.checkin.checkout'

    folio_id = fields.Many2one(comodel_name='hotel.folio', string='Folio')
    partner_id = fields.Many2one(
        comodel_name='res.partner', related='folio_id.partner_id', string='Partner')

    @api.multi
    def checkin(self):
        """When a user checkin, all the room on the folio will become unavailable
        till checkout time.
        """
        hours, minutes = decimal_to_time(self.company_id.checkin_hour)
        can_check_in = datetime.combine(
            date.today(), tm(hours, minutes)) < datetime.now()
        if not can_check_in:
            raise UserError('Guest(s) cannot be checked in earlier than {}'.format(
                self.company_id.checkin_hour))
        for room in self.room_ids:
            if room.is_available():
                room.preoccupy()
        self.write({'state': 'checkin'})
