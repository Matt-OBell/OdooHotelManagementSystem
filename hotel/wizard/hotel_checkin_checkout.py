# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.hotel.helper import decimal_to_time
from datetime import datetime, timedelta, date, time as tm


class HotelCheckinCheckout(models.TransientModel):
    _name = 'wizard.checkin.checkout'

    room_id = fields.Many2one(comodel_name='hotel.room', string='Room')
    folio_id = fields.Many2one(comodel_name='hotel.folio',
                               compute='_compute_folio_id', string='Folio Number')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='folio_id.partner_id',
        string='Partner'
    )
    total_bill = fields.Float(string='Total Bill',
                              related='folio_id.total_amount')
    payment_deposits = fields.Float(string='Deposit',
                                    related='folio_id.payment_deposits')
    amount_due = fields.Float(
        string='Amount Due', compute='_compute_amount_due')
    number_of_days = fields.Integer(
        string='Number of Days', required=True, default=1)

    @api.depends('payment_deposits', 'total_bill')
    def _compute_amount_due(self):
        self.amount_due = self.total_bill - self.payment_deposits

    @api.depends('room_id')
    def _compute_folio_id(self):
        folio_ids = self.room_id.folio_ids
        if folio_ids:
            folio_id = folio_ids.filtered(
                lambda rec: rec.room_id.status in ['on_queue', 'occupied'])
            # There will be may be many folio on queue, so there is need to pick the
            # the lastest folio attached to the room
            if len(folio_id) > 1:
                self.folio = folio_id[-1].id
            else:
                self.folio_id = folio_id.id

    @api.multi
    def checkin(self):
        """When a user checkin, all the room on the folio will become unavailable
        till checkout time.
        """
        folio = self.folio_id
        if folio.payment_deposits <= 0:
            raise UserError(_("""No record of security deposit found on folio {}
                """.format(folio.name)))
        if folio.state != 'on_queue':
            raise UserError(_(
                'Folio {} is not yet to be processed'.format(self.folio_id.name)))
        hours, minutes = decimal_to_time(self.env.user.company_id.checkin_hour)
        can_check_in = datetime.combine(
            date.today(), tm(hours, minutes)) < datetime.now()
        if not can_check_in:
            raise UserError(
                'Guest(s) cannot be checked in earlier than {}'.format(
                    self.env.user.company_id.checkin_hour))
        if self.folio_id.room_id.occupy():
            self.folio_id.write({'state': 'checkin'})

    @api.multi
    def extend_stay(self):
        extend_from = fields.Datetime.from_string(self.folio_id.checkout_date)
        extend_to = timedelta(days=int(self.number_of_days))
        new_checkout_date = extend_from + extend_to
        self.folio_id.write({'checkout_date': new_checkout_date})

    def checkout(self):
        folio = self.folio_id
        if folio.payment_deposits <= 0:
            raise UserError(_("""No record of security deposit found on folio {}
                """.format(folio.name)))
        if folio.state != 'checkin':
            raise UserError(_(
                'Folio {} is not yet to be processed'.format(self.folio_id.name)))

        if self.amount_due <= 0:
            self._checkout(folio)
        else:
            raise UserError(
                'The customer needs to pay all due amount before checkout can be completed.')

    def _checkout(self, folio):
        room = folio.room_id
        folio.write({'state': 'checkout'})
        room.write({'status': 'on_change'})

    def pay_due_amount(self, context):
        """Generate due amount and match it up with the customer invoice."""
        payment = self.env['account.payment'].sudo(self.env.user.id)
        action = {
            'name': 'Deposits',
            'type': 'ir.actions.act_window',
            'res_model': payment._name,
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [['folio_id', '=', self.folio_id.id]],
            'context': {
                'default_folio_id': self.folio_id.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_due
            }
        }
        if not payment.search([('folio_id', '=', self.folio_id.id)]):
            # There is no payment made agaist this folio. we need to make new deposit.
            return action
        action.update(res_id=self.folio_id.id)
        return action
