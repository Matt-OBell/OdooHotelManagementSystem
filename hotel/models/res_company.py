from odoo import fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    checkin_hour = fields.Float(string='Checkin Hour')
    checkout_hour = fields.Float(string='Checkout Hour')
    additional_hours = fields.Integer(
        'Additional Hours', help="""Provide the min hours value for check in,
        checkout days, whatever the hours will be provided here based on that
        extra days will be calculated.""")
