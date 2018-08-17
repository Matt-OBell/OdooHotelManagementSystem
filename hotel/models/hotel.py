# See LICENSE file for full copyright and licensing details.

import time
import datetime
from urllib.request import urlopen as urllib2
from odoo.exceptions import except_orm, ValidationError
from odoo.osv import expression
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _
from decimal import Decimal


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


class HotelFloor(models.Model):

    _name = "hotel.floor"
    _description = "Floor"

    name = fields.Char('Floor Name', size=64, required=True, index=True)
    sequence = fields.Integer('Sequence', size=64, index=True)




# class HotelRoomAmenitiesType(models.Model):

#     _name = 'hotel.room.amenities.type'
#     _description = 'amenities Type'

#     name = fields.Char('Name', size=64, required=True)
#     amenity_id = fields.Many2one('hotel.room.amenities.type', 'Category')
#     child_id = fields.One2many('hotel.room.amenities.type', 'amenity_id',
#                                'Child Categories')

#     @api.multi
#     def name_get(self):
#         def get_names(cat):
#             """ Return the list [cat.name, cat.amenity_id.name, ...] """
#             res = []
#             while cat:
#                 res.append(cat.name)
#                 cat = cat.amenity_id
#             return res
#         return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         if not args:
#             args = []
#         if name:
#             # Be sure name_search is symetric to name_get
#             category_names = name.split(' / ')
#             parents = list(category_names)
#             child = parents.pop()
#             domain = [('name', operator, child)]
#             if parents:
#                 names_ids = self.name_search(' / '.join(parents), args=args,
#                                              operator='ilike', limit=limit)
#                 category_ids = [name_id[0] for name_id in names_ids]
#                 if operator in expression.NEGATIVE_TERM_OPERATORS:
#                     categories = self.search([('id', 'not in', category_ids)])
#                     domain = expression.OR([[('amenity_id', 'in',
#                                               categories.ids)], domain])
#                 else:
#                     domain = expression.AND([[('amenity_id', 'in',
#                                                category_ids)], domain])
#                 for i in range(1, len(category_names)):
#                     domain = [[('name', operator,
#                                 ' / '.join(category_names[-1 - i:]))], domain]
#                     if operator in expression.NEGATIVE_TERM_OPERATORS:
#                         domain = expression.AND(domain)
#                     else:
#                         domain = expression.OR(domain)
#             categories = self.search(expression.AND([domain, args]),
#                                      limit=limit)
#         else:
#             categories = self.search(args, limit=limit)
#         return categories.name_get()


# class HotelRoomAmenities(models.Model):

#     _name = 'hotel.room.amenities'
#     _description = 'Room amenities'

#     product_id = fields.Many2one('product.product', 'Product Category',
#                                  required=True, delegate=True,
#                                  ondelete='cascade')
#     categ_id = fields.Many2one('hotel.room.amenities.type',
#                                string='Amenities Category', required=True)
#     product_manager = fields.Many2one('res.users', string='Product Manager')


class FolioRoomLine(models.Model):

    _name = 'folio.room.line'
    _description = 'Hotel Room Reservation'
    _rec_name = 'room_id'

    room_id = fields.Many2one(comodel_name='hotel.room', string='Room id')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    folio_id = fields.Many2one('hotel.folio', string='Folio Number')
    status = fields.Selection(string='state', related='folio_id.state')







class HotelServiceLine(models.Model):

    @api.multi
    def copy(self, default=None):
        """
        @param self: object pointer
        @param default: dict of default values to be set
        """
        return super(HotelServiceLine, self).copy(default=default)

    @api.model
    def _service_checkin_date(self):
        if 'checkin' in self._context:
            return self._context['checkin']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.model
    def _service_checkout_date(self):
        if 'checkout' in self._context:
            return self._context['checkout']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    _name = 'hotel.service.line'
    _description = 'hotel Service line'

    service_line_id = fields.Many2one('sale.order.line', 'Service Line',
                                      required=True, delegate=True,
                                      ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', 'Folio', ondelete='cascade')
    ser_checkin_date = fields.Datetime('From Date', required=True,
                                       default=_service_checkin_date)
    ser_checkout_date = fields.Datetime('To Date', required=True,
                                        default=_service_checkout_date)

    @api.model
    def create(self, vals, check=True):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel service line.
        """
        if 'folio_id' in vals:
            folio = self.env['hotel.folio'].browse(vals['folio_id'])
            vals.update({'order_id': folio.order_id.id})
        return super(HotelServiceLine, self).create(vals)

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        s_line_obj = self.env['sale.order.line']
        for line in self:
            if line.service_line_id:
                sale_unlink_obj = s_line_obj.browse([line.service_line_id.id])
                sale_unlink_obj.unlink()
        return super(HotelServiceLine, self).unlink()

    @api.onchange('product_id')
    def product_id_change(self):
        """
        @param self: object pointer
        """
        if self.product_id and self.folio_id.partner_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price
            self.product_uom = self.product_id.uom_id
            tax_obj = self.env['account.tax']
            prod = self.product_id
            self.price_unit = tax_obj._fix_tax_included_price(prod.price,
                                                              prod.taxes_id,
                                                              self.tax_id)

    @api.onchange('product_uom')
    def product_uom_change(self):
        """
        @param self: object pointer
        """
        if not self.product_uom:
            self.price_unit = 0.0
            return
        self.price_unit = self.product_id.list_price
        if self.folio_id.partner_id:
            prod = self.product_id.with_context(
                lang=self.folio_id.partner_id.lang,
                partner=self.folio_id.partner_id.id,
                quantity=1,
                date_order=self.folio_id.checkin_date,
                pricelist=self.folio_id.pricelist_id.id,
                uom=self.product_uom.id
            )
            tax_obj = self.env['account.tax']
            self.price_unit = tax_obj._fix_tax_included_price(prod.price,
                                                              prod.taxes_id,
                                                              self.tax_id)

    @api.onchange('ser_checkin_date', 'ser_checkout_date')
    def on_change_checkout(self):
        """
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel service line
        -----------------------------------------------------------------
        @param self: object pointer
        """
        if not self.ser_checkin_date:
            time_a = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.ser_checkin_date = time_a
        if not self.ser_checkout_date:
            self.ser_checkout_date = time_a
        if self.ser_checkout_date < self.ser_checkin_date:
            raise _('Checkout must be greater or equal checkin date')
        if self.ser_checkin_date and self.ser_checkout_date:
            date_a = time.strptime(self.ser_checkout_date,
                                   DEFAULT_SERVER_DATETIME_FORMAT)[:5]
            date_b = time.strptime(self.ser_checkin_date,
                                   DEFAULT_SERVER_DATETIME_FORMAT)[:5]
            diffDate = datetime.datetime(*date_a) - datetime.datetime(*date_b)
            qty = diffDate.days + 1
            self.product_uom_qty = qty

    @api.multi
    def button_confirm(self):
        """
        @param self: object pointer
        """
        for folio in self:
            line = folio.service_line_id
            x = line.button_confirm()
        return x

    @api.multi
    def button_done(self):
        """
        @param self: object pointer
        """
        for folio in self:
            line = folio.service_line_id
            x = line.button_done()
        return x

    @api.multi
    def copy_data(self, default=None):
        """
        @param self: object pointer
        @param default: dict of default values to be set
        """
        sale_line_obj = self.env['sale.order.line'
                                 ].browse(self.service_line_id.id)
        return sale_line_obj.copy_data(default=default)


class HotelServiceType(models.Model):

    _name = "hotel.service.type"
    _description = "Service Type"

    name = fields.Char('Service Name', size=64, required=True)
    service_id = fields.Many2one('hotel.service.type', 'Service Category')
    child_id = fields.One2many('hotel.service.type', 'service_id',
                               'Child Categories')

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.service_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.service_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args,
                                             operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('service_id', 'in',
                                              categories.ids)], domain])
                else:
                    domain = expression.AND([[('service_id', 'in',
                                               category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator,
                                ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]),
                                     limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class HotelServices(models.Model):

    _name = 'hotel.services'
    _description = 'Hotel Services and its charges'

    product_id = fields.Many2one('product.product', 'Service_id',
                                 required=True, ondelete='cascade',
                                 delegate=True)
    categ_id = fields.Many2one('hotel.service.type', string='Service Category',
                               required=True)
    product_manager = fields.Many2one('res.users', string='Product Manager')



class CurrencyExchangeRate(models.Model):

    _name = "currency.exchange"
    _description = "currency"

    @api.depends('input_curr', 'out_curr', 'in_amount')
    def _compute_get_currency(self):
        """
        When you change input_curr, out_curr or in_amount
        it will update the out_amount of the currency exchange
        ------------------------------------------------------
        @param self: object pointer
        """
        for rec in self:
            rec.out_amount = 0.0
            if rec.input_curr:
                result = rec.get_rate(rec.input_curr.name,
                                      rec.out_curr.name)
                if rec.out_curr:
                    rec.rate = result
                    if rec.rate == Decimal('-1.00'):
                        raise except_orm(_('Warning'),
                                         _('Please Check Your \
                                         Network Connectivity.'))
                    rec.out_amount = (float(result) * float(rec.in_amount))

    @api.depends('out_amount', 'tax')
    def _compute_tax_change(self):
        """
        When you change out_amount or tax
        it will update the total of the currency exchange
        -------------------------------------------------
        @param self: object pointer
        """
        for rec in self:
            if rec.out_amount:
                ser_tax = ((rec.out_amount) * (float(rec.tax))) / 100
                rec.total = rec.out_amount + ser_tax

    @api.model
    def get_rate(self, a, b):
        """
        Calculate rate between two currency
        -----------------------------------
        @param self: object pointer
        """
        try:
            url = 'http://finance.yahoo.com/d/quotes.csv?s=%s%s=X&f=l1' % (a,
                                                                           b)
            rate = urllib2.urlopen(url).read().rstrip()
            return Decimal(rate)
        except:
            return Decimal('-1.00')

    name = fields.Char('Reg Number', readonly=True, default='New')
    today_date = fields.Datetime('Date Ordered',
                                 required=True,
                                 default=(lambda *a:
                                          time.strftime
                                          (DEFAULT_SERVER_DATETIME_FORMAT)))
    input_curr = fields.Many2one('res.currency', string='Input Currency',
                                 track_visibility='always')
    in_amount = fields.Float('Amount Taken', size=64, default=1.0, index=True)
    out_curr = fields.Many2one('res.currency', string='Output Currency',
                               track_visibility='always')
    out_amount = fields.Float(compute="_compute_get_currency",
                              string='Subtotal', size=64)
    folio_no = fields.Many2one('hotel.folio', 'Folio Number')
    guest_name = fields.Many2one('res.partner', string='Guest Name')
    room_number = fields.Char(string='Room Number')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
                              ('cancel', 'Cancel')], 'State', default='draft')
    rate = fields.Float(compute="_compute_get_currency",
                        string='Rate (Per Unit)', size=64, readonly=True)
    hotel_id = fields.Many2one('stock.warehouse', 'Hotel Name')
    type = fields.Selection([('cash', 'Cash')], 'Type', default='cash')
    tax = fields.Selection([('2', '2%'), ('5', '5%'), ('10', '10%')],
                           'Service Tax', default='2')
    total = fields.Float(compute="_compute_tax_change", string='Total Amount')

    @api.constrains('out_curr')
    def check_out_curr(self):
        for cur in self:
            if cur.out_curr == cur.input_curr:
                raise ValidationError(_('Input currency and output currency '
                                        'must not be same'))

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if not vals:
            vals = {}
        if self._context is None:
            self._context = {}
        seq_obj = self.env['ir.sequence']
        vals['name'] = seq_obj.next_by_code('currency.exchange') or 'New'
        return super(CurrencyExchangeRate, self).create(vals)

    @api.onchange('folio_no')
    def get_folio_no(self):
        """
        When you change folio_no, based on that it will update
        the guest_name,hotel_id and room_number as well
        ---------------------------------------------------------
        @param self: object pointer
        """
        for rec in self:
            self.guest_name = False
            self.hotel_id = False
            self.room_number = False
            if rec.folio_no and len(rec.folio_no.room_lines) != 0:
                self.guest_name = rec.folio_no.partner_id.id
                self.hotel_id = rec.folio_no.warehouse_id.id
                self.room_number = rec.folio_no.room_lines[0].product_id.name

    @api.multi
    def act_cur_done(self):
        """
        This method is used to change the state
        to done of the currency exchange
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'done'
        return True

    @api.multi
    def act_cur_cancel(self):
        """
        This method is used to change the state
        to cancel of the currency exchange
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'cancel'
        return True

    @api.multi
    def act_cur_cancel_draft(self):
        """
        This method is used to change the state
        to draft of the currency exchange
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'draft'
        return True


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
