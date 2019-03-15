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
    pricelist_id = fields.Many2one('product.pricelist', 'Scheme',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help="Pricelist for current reservation.")
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]},
                                         help="Invoice address for "
                                         "current reservation.")
    number_of_rooms = fields.Integer(string='Number of Rooms',
                                     help="The name and address of the "
                                     "contact that requested the order "
                                     "or quotation.", required=True, default=1)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          readonly=True,
                                          states={'draft':
                                                  [('readonly', False)]},
                                          help="Delivery address"
                                          "for current reservation. ")
    arrival_date = fields.Date(string='Check-in', required=True)
    departure_date = fields.Date(string='Check-out', required=True)
    adults = fields.Integer(string='Adults', default=1,
                            help='List of adults there in guest list. ')
    children = fields.Integer(
        string='Children', default=0, help='Number of children there in guest list.')
    reserved_room_ids = fields.Many2many('hotel.room', string='Reservation Line',
                                         help='Hotel room reservation details.', store=True, compute='_compute_room_reservation')

    state = fields.Selection(selection=STATES, string='State', default='draft')
    folio_id = fields.Many2one('hotel.folio', string='Folio')

    @api.depends('number_of_rooms')
    def _compute_room_reservation(self):
        rooms = self.env['hotel.room'].search([('status', '=', 'vacant')])
        if len(rooms) < self.number_of_rooms:
            raise ValidationError(
                "Sorry, there are only {} vacant room(s) available at the moment".format(len(rooms)))
        room_ids = [(4, room_id[1].id) for room_id in enumerate(
            rooms) if room_id[0] <= (self.number_of_rooms - 1)]
        self.reserved_room_ids = room_ids

    # def reserved_rooms_ids(self):
    #     ids = []
    #     reservations = self.search([('state', '=', 'reserve')])
    #     for reservation in reservations:
    #         for room_id in reservation.reservation_line_ids:
    #             ids.append(room_id.room_id.id)
    #     return list(set(ids))

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
    def reserve(self):
        return self.write({'state': 'reserve'})

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


class ReservationSummary(models.Model):

    _name = 'room.reservation.summary'
    _description = 'Room reservation summary'

    name = fields.Char(string='Reservation Summary', default='Reservations Summary',
                       invisible=True)
    date_from = fields.Datetime(string='Date From')
    date_to = fields.Datetime(string='Date To')
    summary_header = fields.Text(string='Summary Header')
    room_summary = fields.Text(string='Room Summary')

    def list_date_between(self, date_from, date_to):
        date_format = ['Room', 'Jan-1-2018',
                       'Jan-2-2018', 'Jan-3-2018', 'Jan-4-2018']
        return date_format

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        res = super(ReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        date_between = self.list_date_between(dt_from, dt_to)
        res.update({'date_from': dt_from, 'date_to': dt_to,
                    'summary_header': date_between})

        if not self.date_from and self.date_to:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(date_today.year,
                                          date_today.month, 1, 0, 0, 0)
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(last_temp_day.year,
                                         last_temp_day.month,
                                         last_temp_day.day, 23, 59, 59)
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({'date_from': date_froms, 'date_to': date_ends})
        print(res, '**********************************')
        return res

    @api.multi
    def room_reservation(self):
        """
        @param self: object pointer
        """
        mod_obj = self.env['ir.model.data']
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),
                                         ('name', '=',
                                          'view_hotel_reservation_form')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {'name': _('Reconcile Write-Off'),
                'context': self._context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hotel.reservation',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    @api.onchange('date_from', 'date_to')
    def get_room_summary(self):
        import random
        a = random.randrange(1, 90)
        print('***********************************',
              self.date_to, self.date_from)
        self.summary_header = list(range(1, a))
