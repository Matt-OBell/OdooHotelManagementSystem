# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HotelReservationWizard(models.TransientModel):

    _name = 'hotel.reservation.wizard'

    date_start = fields.Datetime('Start Date', required=True)
    date_end = fields.Datetime('End Date', required=True)

    @api.multi
    def report_reservation_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env.ref('hotel_reservation.hotel_roomres_details').report_action([], data=data, config=False)

    @api.multi
    def report_checkin_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0],
        }
        return self.env.ref('hotel_reservation.hotel_checkin_details').report_action(self, data=data, config=False)

    @api.multi
    def report_checkout_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env.ref('hotel_reservation.hotel_checkout_details').report_action(self, data=data, config=False)

    @api.multi
    def report_maxroom_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env.ref('hotel_reservation.hotel_maxroom_details').report_action(self, data=data, config=False)


class MakeFolioWizard(models.TransientModel):

    _name = 'wizard.make.folio'

    grouped = fields.Boolean('Group the Folios')

    @api.multi
    def makeFolios(self):
        order_obj = self.env['hotel.reservation']
        newinv = []
        for order in order_obj.browse(self.env.context.get('active_ids', [])):
            for folio in order.folio_id:
                newinv.append(folio.id)
        return {
            'domain': "[('id','in', [" + ','.join(map(str, newinv)) + "])]",
            'name': 'Folios',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hotel.folio',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
