from odoo import api, fields, models

class ProductTemplate(models.Model):

    _inherit = "product.template"

    type = fields.Selection(selection_add=[('amenity', 'Amenity')])