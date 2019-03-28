from odoo import fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    checkin_hour = fields.Char(string='Checkin Hour', default=2.00)
    checkout_hour = fields.Char(string='Checkout Hour', default=11.00)
    additional_hours = fields.Integer(
        'Additional Hours', help="""Provide the min hours value for check in,
        checkout days, whatever the hours will be provided here based on that
        extra days will be calculated.""")
