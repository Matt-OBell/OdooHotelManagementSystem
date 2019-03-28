"""."""
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.exceptions import except_orm, ValidationError, UserError
import pytz

STATES = [
    ('draft', 'Draft'),
    ('reserve', 'Reserve'),
    ('cancel', 'Cancel'),
    ('done', 'Done')
]


def _string_to_datetime_tz(rec, timestamp):
    return fields.Datetime.context_timestamp(rec, timestamp)


class Reservation(models.Model):

    _name = 'hotel.reservation'
    _description = "Hotel Reservation"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reservation')
    partner_id = fields.Many2one('res.partner', string='Guest', readonly=True,
                                 index=True,
                                 required=True,
                                 states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one('product.pricelist', 'Price List',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help="Pricelist for current reservation.")
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]},
                                         help="Invoice address for "
                                         "current reservation.")
    number_of_rooms = fields.Integer(
        string='Number of Rooms', required=True, compute='_compute_number_of_rooms')
    night = fields.Integer(string='Night', states={
                           'draft': [('readonly', False)]}, default=1)
    reservation_line_ids = fields.One2many(
        'hotel.reservation.line', 'reservation_id', string='Reservation Line')
    payment_deposits = fields.Float(
        string='Deposits', compute='_compute_payment_deposit')

    state = fields.Selection(selection=STATES, string='State', default='draft')
    folio_id = fields.Many2one('hotel.folio', string='Folio')
    amount_total = fields.Float(
        string='Amount Total', compute='_compute_amount_total')
    guest_company_id = fields.Many2one('res.partner', string='Company')

    def _compute_payment_deposit(self):
        payment = self.env['account.payment'].sudo(self.env.user.id)
        payments = payment.search(
            [('reservation_id', '=', self.id), ('state', '!=', 'draft')])
        self.payment_deposits = sum([payment.amount for payment in payments])

    @api.depends('reservation_line_ids')
    def _compute_number_of_rooms(self):
        """Compute the number of line items which is also the number of reserved rooms"""
        for recordset in self:
            self.number_of_rooms = len(recordset.reservation_line_ids)

    @api.depends('reservation_line_ids', 'night')
    def _compute_amount_total(self):
        for record in self:
            self.amount_total = abs(sum(
                [line.room_id.total_price for line in record.reservation_line_ids]) * record.night)

    @api.multi
    def make_payment_deposit(self):
        payment = self.env['account.payment'].sudo(self.env.user.id)
        action = {
            'name': 'Deposits',
            'type': 'ir.actions.act_window',
            'res_model': payment._name,
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [['reservation_id', '=', self.id]],
            'context': {
                'default_reservation_id': self.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total
            }
        }
        if not payment.search([('reservation_id', '=', self.id)]):
            # There is no payment made agaist this folio. we need to make new deposit.
            return action
        action.update(res_id=self.id)
        return action

    @api.multi
    def unlink(self):
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Reservation in %s\
                state.') % (reserv_rec.state))
        return super(Reservation, self).unlink()

    @api.constrains('arrival_date', 'departure_date')
    def _check_arrival_date_departure_date_dates(self):
        """
        when current date is less then arrival_date date or departure_date 
        date should be greater than the arrival_date date.
        """
        if self.departure_date and self.arrival_date:
            if fields.Date.from_string(self.arrival_date) < fields.Date.from_string(fields.Date.today()):
                # _string_to_datetime_tz(self, fields.Datetime.from_string(self.arrival_date)), _string_to_datetime_tz(self,datetime.now())
                raise UserError(
                    'Arrival date date should be greater than the current date.')
            if fields.Date.from_string(self.departure_date) < fields.Date.from_string(self.arrival_date):
                raise UserError(
                    'Departure date date should be greater than arrival_date date.')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        """
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.multi
    def check_overlap(self, date1, date2):
        delta = date2 - date1
        return set([date1 + timedelta(days=i) for i in range(delta.days + 1)])

    @api.multi
    def reservation(self):
        for rec in self:
            for room in rec.reservation_line_ids:
                room.write({'status': 'reserved'})
            rec.write({'state': 'reserve'})

    @api.multi
    def cancel(self):
        """
        This method cancel recordset for hotel room reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: cancel record set for hotel room reservation line.
        """
        if self.state in ['draft', 'reserve']:
            return self.write({'state': 'cancel'})

    @api.multi
    def set_to_draft_reservation(self):
        return self.write({'state': 'draft'})

    @api.multi
    def send_reservation_maill(self):
        """
        This function opens a window to compose an email,
        template message loaded by default.
        @param self: object pointer
        """
        ir_model_data = self.env['ir.model.data']
        template_id = self.env.ref(
            'hotel_reservation.email_template_hotel_reservation')
        try:
            compose_form_id = (ir_model_data.get_object_reference
                               ('mail',
                                'email_compose_message_wizard_form')[1])
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hotel.reservation',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
            'force_send': True,
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
            'force_send': True
        }

    @api.multi
    def folio(self):
        """
        This method is meant redirection to folio or to create new hotel folio.
        -----------------------------------------
        @param self: The object pointer
        @return: new record set for hotel folio.
        """
        folio = self.env['hotel.folio']
        if self.folio_id:
            pass
            # redirect to folio
        else:  # create new folio and redirect
            room_ids = [
                reservation.room_id.id for reservation in self.reservation_line_ids]
            vals = {
                'partner_id': self.partner_id.id,
                'checkin_date': self.arrival_date,
                'checkout_date': self.departure_date,
                'room_ids': [[6, False, room_ids]],
                'amenity_ids': [[6, False, []]],
                'reservation_id': self.id
            }
            folio = folio.create(vals)
            self.write({'folio_id': folio.id, 'state': 'done'})

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.

        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vals.update(name=self.env['ir.sequence'].next_by_code(
            'hotel.reservation'))
        return super(Reservation, self).create(vals)
