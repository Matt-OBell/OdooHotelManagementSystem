# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HotelCheckinCheckout(models.TransientModel):
    _name = 'wizard.checkin.checkout'
 

    folio_id = fields.Many2one(comodel_name='hotel.folio', string='Folio')
    partner_id = fields.Many2one(comodel_name='res.partner', related='folio_id.partner_id', string='Partner')

    # @api.multi
    # def print_report(self):
    #     data = {
    #         'ids': self.ids,
    #         'model': 'hotel.folio',
    #         'form': self.read(['date_start', 'date_end'])[0]
    #     }
    #     return self.env.ref('hotel.report_hotel_management').report_action(self, data=data, config=False)
