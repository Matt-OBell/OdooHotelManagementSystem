from datetime import datetime, timedelta, date, time as tm

from odoo import api, fields, models, _


import time
from urllib.request import urlopen as urllib2
from odoo.exceptions import except_orm, ValidationError, MissingError, UserError
from odoo.osv import expression
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT

from decimal import Decimal

_STATES = [
    ('draft', 'Open'),
    ('on_queue', 'On-Queue'),
    ('checkin', 'Checked In'),
    ('checkout', 'Checkout'),
    ('cance', 'Cancel'),
]

HOTEL_POLICY = [
    ('prepaid', 'On Booking'),
    ('manual', 'On Check In'),
    ('picking', 'On Checkout')
]

CLIENT_TYPE = [
    ('is_corporate', 'Corporate'),
    ('is_normal', 'Private')
]


def _offset_format_timestamp1(src_tstamp_str, src_format, dst_format,
                              ignore_unparsable_time=True, context=None):
    """
    Convert a source timeStamp string into a destination timeStamp string,
    attempting to apply the correct offset if both the server and local
    timeZone are recognized,or no offset at all if they aren't or if
    tz_offset is false (i.e. assuming they are both in the same TZ).

    @param src_tstamp_str: the STR value containing the timeStamp.
    @param src_format: the format to use when parsing the local timeStamp.
    @param dst_format: the format to use when formatting the resulting
     timeStamp.
    @param server_to_client: specify timeZone offset direction (server=src
                             and client=dest if True, or client=src and
                             server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str
                                   cannot be parsed using src_format or
                                   formatted using dst_format.
    @return: destination formatted timestamp, expressed in the destination
             timezone if possible and if tz_offset is true, or src_tstamp_str
             if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False
    res = src_tstamp_str
    if src_format and dst_format:
        try:
            # dt_value needs to be a datetime.datetime object\
            # (so notime.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.datetime.strptime(src_tstamp_str, src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone(context['tz'])
                    dst_tz = pytz.timezone('UTC')
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class Folio(models.Model):
    """As soon as the guest checks in to a hotel a guest file folio is opened, 
    all the transactions pertaining to the stay in the room,consumption of 
    food & beverages or use of any facility is posted directly or 
    indirectly onto the guest folio. 

    The cash or credit payments are both included. It is like a book of accounting.
    Upon checking out the the guest is required to settle the amount payable in 
    the guest folio. Folio is considered as the master bill in the hotel 
    which is also known as Guest Account Card. 

    A guest folio contain all transactions of both cash and credit occurred by each
    resident guests.

    Just after the guest/customer entry, the front desk clerk create a guest 
    folio with the inclusion of:

    Guest/customer name
    Room number
    Date of arrival
    Date of departure
    Room rate
    Guest address
    Billing instruction to the cashier .ie line items
    """

    @api.model
    def _get_checkin_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        return _offset_format_timestamp1(time.strftime("%Y-%m-%d 12:00:00"),
                                         DEFAULT_SERVER_DATETIME_FORMAT,
                                         DEFAULT_SERVER_DATETIME_FORMAT,
                                         ignore_unparsable_time=True,
                                         context={'tz': to_zone})

    @api.model
    def _get_checkout_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        tm_delta = timedelta(days=1)
        return datetime.strptime(_offset_format_timestamp1
                                 (time.strftime("%Y-%m-%d 12:00:00"),
                                  DEFAULT_SERVER_DATETIME_FORMAT,
                                  DEFAULT_SERVER_DATETIME_FORMAT,
                                  ignore_unparsable_time=True,
                                  context={'tz': to_zone}),
                                 '%Y-%m-%d %H:%M:%S') + tm_delta

    _name = 'hotel.folio'
    _description = 'Guest Account Card'
    _order = 'id desc'

    name = fields.Char('Number', readonly=True, default='/')
    invoice_id = fields.Many2one(
        'account.invoice', string='Invoice', copy=False)
    partner_id = fields.Many2one('res.partner', string='Guest', copy=False,
                                 domain=[('company_type', '=', 'person')])
    corporate_id = fields.Many2one('res.partner', string='Corporation',
                                   copy=False, domain=[('company_type', '=', 'company')])
    state = fields.Selection(
        selection=_STATES, string='State', default='draft')
    checkin_date = fields.Datetime(string='Arrival Date', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   default=_get_checkin_date)
    checkout_date = fields.Datetime(string='Departure Date', required=True, readonly=True,
                                    states={'draft': [('readonly', False)]},
                                    default=_get_checkout_date)
    room_id = fields.Many2one('hotel.room', string='Room')
    price = fields.Float(string='Price', compute='_compute_room_price', store=True)
    service_ids = fields.Many2many('hotel.services', string='Services')
    hotel_policy = fields.Selection(HOTEL_POLICY, string='Hotel Policy', default='manual',
                                    help="Hotel policy for payment that "
                                    "either the guest has to payment at "
                                    "booking time or check-in "
                                    "check-out time.")
    duration = fields.Integer(string='Duration in Days',
                              help="Number of days which will automatically "
                              "count from the check-in and check-out date. ", compute='_compute_duration', store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get(), required=True)
    payment_deposits = fields.Float(
        string='Deposits', compute='_compute_payment_deposit')
    client_type = fields.Selection(
        CLIENT_TYPE, string='Type', default='is_normal')
    total_amount = fields.Float(
        string='Total Bill', compute='_compute_total_amount')
    source = fields.Char(string='Source')


    @api.depends('duration')
    def _compute_room_price(self):
        for record in self:
            record.price = record.room_id.total_price * record.duration


    @api.multi
    def checkin(self):
        """Open Checkout wizard"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.checkin.checkout",
            "views": [[self.env.ref('hotel.wizard_checkin_checkin_wizard').id, "form"]],
            "context": {'default_room_id': self.room_id.id},
            "target": "new",
        }

    @api.multi
    def checkout(self):
        """Open Checkout wizard"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.checkin.checkout",
            "views": [[self.env.ref('hotel.wizard_checkin_checkout_wizard').id, "form"]],
            "context": {'default_room_id': self.room_id.id},
            "target": "new",
        }



    # corporate_client_child_ids = fields.Many2many(
    #     'res.partner', string='Guests')

    # @api.onchange('client_type', 'corporate_id')
    # def _onchange_client_type(self):
    #     if self.client_type == 'is_corporate':
    #         child_ids = self.corporate_id.child_ids.ids
    #         self.corporate_client_child_ids = child_ids

    @api.multi
    def on_queue(self):
        status = [
            'occupied', 'on_change', 'cleaning_in_progress',
            'on_queue', 'out_of_order', 'out_of_service'
        ]
        for folio in self:
            if not folio.room_id:
                raise MissingError('A room needs to be attached to Folio')
            if folio.room_id.status not in status:
                folio.room_id.write({'status': 'on_queue'})
                folio.write({'state': 'on_queue'})
            else:
                raise UserError(
                    _('The selected room is not available at the moment'))

    @api.multi
    def _calculate_total_amount(self):
        """Calculate amount total should be overiden by the child class"""
        return sum([service_id.lst_price for service_id in self.service_ids])

    @api.depends('service_ids')
    def _compute_total_amount(self):
        for folio in self:
            folio.total_amount = folio._calculate_total_amount() + folio.price

    def _compute_payment_deposit(self):
        payment = self.env['account.payment'].sudo(self.env.user.id)
        payments = payment.search(
            [('folio_id', '=', self.id), ('state', '!=', 'draft')])
        self.payment_deposits = sum([payment.amount for payment in payments])


    @api.model
    def create(self, values):
        values.update(name=self.env['ir.sequence'].next_by_code('hotel.folio'))
        return super(Folio, self).create(values)

    @api.multi
    def advance_deposits(self):
        payment = self.env['account.payment'].sudo(self.env.user.id)
        action = {
            'name': 'Deposits',
            'type': 'ir.actions.act_window',
            'res_model': payment._name,
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [['folio_id', '=', self.id]],
            'context': {
                'default_folio_id': self.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.total_amount
            }
        }
        if not payment.search([('folio_id', '=', self.id)]):
            # There is no payment made agaist this folio. we need to make new deposit.
            return action
        action.update(res_id=self.id)
        return action

    def _sojourn(self, checkin, checkout):
        adjustment, one_day = 0, 86400.0  # 60 * 60 * 24
        total_seconds = (checkout - checkin).total_seconds()
        days = int((total_seconds + adjustment) /
                   one_day) if int((total_seconds + adjustment) / one_day) > 0 else 1
        return days

    @api.depends('checkout_date', 'checkin_date')
    def _compute_duration(self):
        """
        This method gives the duration between check in and checkout
        if customer will leave only for some hour it would be considers
        as a whole day.If customer will check in checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        """
        if self.checkin_date and self.checkout_date:
            checkin = fields.Datetime.from_string(self.checkin_date)
            checkout = fields.Datetime.from_string(self.checkout_date)
            self.duration = self._sojourn(checkin, checkout)

    @api.multi
    def extend_stay(self):
        """
        @param self: object pointer
        """
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.checkin.checkout",
            "views": [[self.env.ref('hotel.wizard_extend_stay_wizard').id, "form"]],
            "context": {'default_folio_id': self.id},
            "target": "new",
        }

    @api.multi
    def action_done(self):
        self.state = 'done'

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        @param self: object pointer
        """
        room_lst = []
        invoice_id = (self.order_id.action_invoice_create(grouped=False,
                                                          final=False))
        for line in self:
            values = {'invoiced': True,
                      'hotel_invoice_id': invoice_id
                      }
            line.write(values)
            for rec in line.room_lines:
                room_lst.append(rec.product_id)
            for room in room_lst:
                room_obj = self.env['hotel.room'
                                    ].search([('name', '=', room.name)])
                room_obj.write({'isroom': True})
        return invoice_id

    @api.multi
    def action_invoice_cancel(self):
        """
        @param self: object pointer
        """
        if not self.order_id:
            raise except_orm(_('Warning'), _('Order id is not available'))
        for sale in self:
            for line in sale.order_line:
                line.write({'invoiced': 'invoiced'})
        self.state = 'invoice_except'
        return self.order_id.action_invoice_cancel

    @api.multi
    def action_cancel(self):
        """
        @param self: object pointer
        """
        if not self.order_id:
            raise except_orm(_('Warning'), _('Order id is not available'))
        for sale in self:
            for invoice in sale.invoice_ids:
                invoice.state = 'cancel'
        return self.order_id.action_cancel()

    @api.multi
    def action_cancel_draft(self):
        """
        @param self: object pointer
        """
        if not len(self._ids):
            return False
        query = "select id from sale_order_line \
        where order_id IN %s and state=%s"
        self._cr.execute(query, (tuple(self._ids), 'cancel'))
        cr1 = self._cr
        line_ids = map(lambda x: x[0], cr1.fetchall())
        self.write({'state': 'draft', 'invoice_ids': [], 'shipped': 0})
        sale_line_obj = self.env['sale.order.line'].browse(line_ids)
        sale_line_obj.write({'invoiced': False, 'state': 'draft',
                             'invoice_lines': [(6, 0, [])]})
        return True
