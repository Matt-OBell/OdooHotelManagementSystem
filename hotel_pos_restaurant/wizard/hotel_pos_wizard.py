# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class OrderReportWizard(models.TransientModel):
    _name = 'order.report.wizard'
    _rec_name = 'date_start'

    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')
    check = fields.Boolean('With Details')

    @api.multi
    def print_pos_report(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.folio',
            'form': self.read(['date_start', 'date_end', 'check'])[0]
        }
        return self.env.ref('hotel_pos_restaurant.report_hotel_pos_order').report_action(self, data=data, config=False)
