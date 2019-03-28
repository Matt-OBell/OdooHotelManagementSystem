"""."""
from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if self._context.get('folio_id'):
            folio = self.env['hotel.folio'].browse(self._context['folio_id'])
            folio.write({'hotel_invoice_id': res.id,
                         'invoice_status': 'invoiced'})
        return res
