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
    ('confirm', 'Confirm'),
    ('cancel', 'Cancel'),
    ('done', 'Done')
]


class HotelReservation(models.Model):

    _name = 'hotel.reservation'
    _description = "Hotel Reservation"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reservation')
    partner_id = fields.Many2one('res.partner', 'Guest Name', readonly=True,
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
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       readonly=True,
                                       states={'draft':
                                               [('readonly', False)]},
                                       help="The name and address of the "
                                       "contact that requested the order "
                                       "or quotation.")
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          readonly=True,
                                          states={'draft':
                                                  [('readonly', False)]},
                                          help="Delivery address"
                                          "for current reservation. ")
    arrival_date = fields.Datetime(string='Arrival Date', required=True)
    departure_date = fields.Datetime(string='Departure Date', required=True)
    adults = fields.Integer(string='Adults', default=1,
                            help='List of adults there in guest list. ')
    children = fields.Integer(
        string='Children', default=0, help='Number of children there in guest list.')
    reservation_line_ids = fields.One2many('hotel.reservation.line', 'line_id', string='Reservation Line',
                                           help='Hotel room reservation details.',
                                           states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=STATES, string='State', default='draft')
    folio_id = fields.Many2many('hotel.folio', 'hotel_folio_reservation_rel',
                                'order_id', 'invoice_id', string='Folio')
    dummy = fields.Datetime('Dummy')

    def reserved_rooms_ids(self):
        ids = []
        reservations = self.search([('state', '=', 'confirm')])
        for reservation in reservations:
            for room_id in reservation.reservation_line_ids:
                ids.append(room_id.room_id.id)
        return list(set(ids))

    @api.multi
    def unlink(self):
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Reservation in %s\
                state.') % (reserv_rec.state))
        return super(HotelReservation, self).unlink()

    # @api.constrains('reservation_line', 'adults', 'children')
    # def check_reservation_rooms(self):
    #     """
    #     This method is used to validate the reservation_line.
    #     -----------------------------------------------------
    #     @param self: object pointer
    #     @return: raise a warning depending on the validation
    #     """
    #     for reservation in self:
    #         if reservation.state not in [None, 'draft']:
    #             cap = 0
    #             for rec in reservation.reservation_line:
    #                 if len(rec.reserve) == 0:
    #                     raise ValidationError(_('Please Select Rooms For Reservation.'))
    #                 for room in rec.reserve:
    #                     cap += room.capacity
    #             if (reservation.adults + reservation.children) > cap:
    #                 raise ValidationError(_('Room Capacity Exceeded Please Select Rooms According to Members Accomodation.'))
    #             if reservation.adults <= 0:
    #                 raise ValidationError(_('Adults must be more than 0'))

    @api.constrains('arrival_date', 'departure_date')
    def _check_arrival_date_departure_date_dates(self):
        """
        when current date is less then arrival_date date or departure_date 
        date should be greater than the arrival_date date.
        """
        if self.departure_date and self.arrival_date:
            if fields.Datetime.from_string(self.arrival_date) <= fields.Datetime.from_string(fields.Datetime.now()):
                raise UserError(
                    'arrival_date date should be greater than the current date.')
            if fields.Datetime.from_string(self.departure_date) <= fields.Datetime.from_string(self.arrival_date):
                raise UserError(
                    'departure_date date should be greater than arrival_date date.')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
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
    def confirm(self):
        """
        This method confirm the resevation record
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel room reservation line.
        """
        if not self.reservation_line_ids:
            raise UserError('The reservation line is missing')
        return self.write({'state': 'confirm'})

    @api.multi
    def cancel(self):
        """
        This method cancel recordset for hotel room reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: cancel record set for hotel room reservation line.
        """
        if self.state in ['draft', 'confirm']:
            return self.write({'state': 'cancel', 'reservation_line_ids': [[6, False, []]]})

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
        assert len(self._ids) == 1, 'This is for a single id at a time.'
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = (ir_model_data.get_object_reference
                           ('hotel_reservation',
                            'email_template_hotel_reservation')[1])
        except ValueError:
            template_id = False
        try:
            compose_form_id = (ir_model_data.get_object_reference
                               ('mail',
                                'email_compose_message_wizard_form')[1])
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hotel.reservation',
            'default_res_id': self._ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
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
        hotel_folio_obj = self.env['hotel.folio']

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.

        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vals.update(name=self.env['ir.sequence'].next_by_code(
            'hotel.reservation'))
        return super(HotelReservation, self).create(vals)


class RoomReservationSummary(models.Model):

    _name = 'room.reservation.summary'
    _description = 'Room reservation summary'

    name = fields.Char('Reservation Summary', default='Reservations Summary',
                       invisible=True)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    summary_header = fields.Text('Summary Header')
    room_summary = fields.Text('Room Summary')

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(RoomReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        res.update({'date_from': dt_from, 'date_to': dt_to})

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
        """
        @param self: object pointer
         """
        res = {}
        all_detail = []
        room_obj = self.env['hotel.room']
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        user_obj = self.env['res.users']
        date_range_list = []
        main_header = []
        summary_header_list = ['Rooms']
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise except_orm(_('User Error!'),
                                 _('Please Check Time period Date \
                                 From can\'t be greater than Date To !'))
            if self._context.get('tz', False):
                timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            d_frm_obj = datetime.strptime(self.date_from, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            d_to_obj = datetime.strptime(self.date_to, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = d_frm_obj
            while(temp_date <= d_to_obj):
                val = ''
                val = (str(temp_date.strftime("%a")) + ' ' +
                       str(temp_date.strftime("%b")) + ' ' +
                       str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime
                                       (dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            room_ids = room_obj.search([])
            all_room_detail = []
            for room in room_ids:
                room_detail = {}
                room_list_stats = []
                room_detail.update({'name': room.name or ''})
                if not room.room_reservation_line_ids and \
                   not room.room_line_ids:
                    for chk_date in date_range_list:
                        room_list_stats.append({'state': 'Free',
                                                'date': chk_date,
                                                'room_id': room.id})
                else:
                    for chk_date in date_range_list:
                        ch_dt = chk_date[:10] + ' 23:59:59'
                        ttime = datetime.strptime(ch_dt, dt)
                        c = ttime.replace(tzinfo=timezone).\
                            astimezone(pytz.timezone('UTC'))
                        chk_date = c.strftime(dt)
                        reserline_ids = room.room_reservation_line_ids.ids
                        reservline_ids = (reservation_line_obj.search
                                          ([('id', 'in', reserline_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('state', '=', 'assigned')
                                            ]))
                        if not reservline_ids:
                            sdt = dt
                            chk_date = datetime.strptime(chk_date, sdt)
                            chk_date = datetime.\
                                strftime(chk_date - timedelta(days=1), sdt)
                            reservline_ids = (reservation_line_obj.search
                                              ([('id', 'in', reserline_ids),
                                                ('check_in', '<=', chk_date),
                                                ('check_out', '>=', chk_date),
                                                ('state', '=', 'assigned')]))
                            for res_room in reservline_ids:
                                rrci = res_room.check_in
                                rrco = res_room.check_out
                                cid = datetime.strptime(rrci, dt)
                                cod = datetime.strptime(rrco, dt)
                                dur = cod - cid
                                if room_list_stats:
                                    count = 0
                                    for rlist in room_list_stats:
                                        cidst = datetime.strftime(cid, dt)
                                        codst = datetime.strftime(cod, dt)
                                        rm_id = res_room.room_id.id
                                        ci = rlist.get('date') >= cidst
                                        co = rlist.get('date') <= codst
                                        rm = rlist.get('room_id') == rm_id
                                        st = rlist.get('state') == 'Reserved'
                                        if ci and co and rm and st:
                                            count += 1
                                    if count - dur.days == 0:
                                        c_id1 = user_obj.browse(self._uid)
                                        c_id = c_id1.company_id
                                        con_add = 0
                                        amin = 0.0
                                        if c_id:
                                            con_add = c_id.additional_hours
#                                        When configured_addition_hours is
#                                        greater than zero then we calculate
#                                        additional minutes
                                        if con_add > 0:
                                            amin = abs(con_add * 60)
                                        hr_dur = abs((dur.seconds / 60))
#                                        When additional minutes is greater
#                                        than zero then check duration with
#                                        extra minutes and give the room
#                                        reservation status is reserved or
#                                        free
                                        if amin > 0:
                                            if hr_dur >= amin:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                        else:
                                            if hr_dur > 0:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                    else:
                                        reservline_ids = False
                        fol_room_line_ids = room.room_line_ids.ids
                        chk_state = ['draft', 'cancel']
                        folio_resrv_ids = (folio_room_line_obj.search
                                           ([('id', 'in', fol_room_line_ids),
                                             ('check_in', '<=', chk_date),
                                             ('check_out', '>=', chk_date),
                                             ('status', 'not in', chk_state)
                                             ]))
                        if reservline_ids or folio_resrv_ids:
                            room_list_stats.append({'state': 'Reserved',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        else:
                            room_list_stats.append({'state': 'Free',
                                                    'date': chk_date,
                                                    'room_id': room.id})

                room_detail.update({'value': room_list_stats})
                all_room_detail.append(room_detail)
            main_header.append({'header': summary_header_list})
            self.summary_header = str(main_header)
            self.room_summary = str(all_room_detail)
        return res


class QuickRoomReservation(models.TransientModel):
    _name = 'quick.room.reservation'
    _description = 'Quick Room Reservation'

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True)
    check_in = fields.Datetime('Check In', required=True)
    check_out = fields.Datetime('Check Out', required=True)
    room_id = fields.Many2one('hotel.room', 'Room', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Hotel', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'pricelist')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         required=True)
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       required=True)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          required=True)
    adults = fields.Integer('Adults', size=64)

    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        """
        When you change departure_date or arrival_date it will check whether
        departure_date date should be greater than arrival_date date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        """
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise except_orm(_('Warning'),
                                 _('departure_date date should be greater \
                                 than arrival_date date.'))

    @api.onchange('partner_id')
    def onchange_partner_id_res(self):
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

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(QuickRoomReservation, self).default_get(fields)
        if self._context:
            keys = self._context.keys()
            if 'date' in keys:
                res.update({'check_in': self._context['date']})
            if 'room_id' in keys:
                roomid = self._context['room_id']
                res.update({'room_id': int(roomid)})
        return res

    @api.multi
    def room_reserve(self):
        """
        This method create a new record for hotel.reservation
        -----------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel reservation.
        """
        hotel_res_obj = self.env['hotel.reservation']
        for res in self:
            rec = (hotel_res_obj.create
                   ({'partner_id': res.partner_id.id,
                     'partner_invoice_id': res.partner_invoice_id.id,
                     'partner_order_id': res.partner_order_id.id,
                     'partner_shipping_id': res.partner_shipping_id.id,
                     'arrival_date': res.check_in,
                     'departure_date': res.check_out,
                     'warehouse_id': res.warehouse_id.id,
                     'pricelist_id': res.pricelist_id.id,
                     'adults': res.adults,
                     'reservation_line': [(0, 0,
                                           {'reserve': [(6, 0,
                                                         [res.room_id.id])],
                                            'name': (res.room_id and
                                                     res.room_id.name or '')
                                            })]
                     }))
        return rec
