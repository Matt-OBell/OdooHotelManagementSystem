"""."""
from odoo import api, fields, models


class AccountPayment(models.Model):
    """docstring for AccountPayment"""

    _inherit = 'account.payment'

    reservation_id = fields.Many2one(comodel_name='hotel.reservation', string='Reservation')