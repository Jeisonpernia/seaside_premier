from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import calendar, logging

_logger = logging.getLogger(__name__)


class MiscellaneousFee(models.TransientModel):
    _name = 'miscellaneous.fee.wizard'

    misc_rate = fields.Float(string="Miscellaneous Rate(%)")
    product_amount = fields.Float(string="Net Total List Price", readonly=True)
    misc_fee = fields.Float(string="Miscellaneous Fee")

    @api.model
    def default_get(self, vals):
        res = super(MiscellaneousFee, self).default_get(vals)
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        gross_membership_fee = 0.0
        coupons = 0.0
        for order_line in sale_form.order_line:
            if order_line.product_id.membership:
                gross_membership_fee += order_line.price_subtotal
            if order_line.product_id.is_coupon:
                coupons += order_line.price_subtotal
        res.update({'product_amount': gross_membership_fee + coupons})
        return res

    @api.onchange('misc_rate')
    def onchange_misc_fee(self):
        if self.misc_rate:
            self.misc_fee = self.product_amount*(self.misc_rate/100)

    @api.multi
    def create_misc_line(self):
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        misc_product = self.env['product.product'].search([('name','ilike','Misc')])
        if not misc_product:
            misc_product = self.env['product.product'].create({'name': 'Miscellaneous Fee',
                                                               'type': 'service',
                                                               'invoice_policy': 'order',
                                                               'company_id': False,
                                                               })
        misc_line_found = False
        if self.misc_fee != 0.0:
            for order_line in sale_form.order_line:
                if "misc" in str(order_line.product_id.name).lower():
                    misc_line_found = True
                    order_line.update({'price_unit': self.misc_fee,
                                       'price_subtotal': self.misc_fee})
                    break
            if not misc_line_found:
                sale_form.write({'order_line':[(0,0,{'name': misc_product.name + "("+str(self.misc_rate)+"%)",
                                                     'price_unit': self.misc_fee,
                                                     'product_uom_qty': 1.0,
                                                     'order_id': sale_form.id,
                                                     'discount': 0.0,
                                                     'product_uom': misc_product.uom_id.id,
                                                     'product_id': misc_product.id,
                                                     })]
                                 })
                for order_line in sale_form.order_line:
                    if "misc" in str(order_line.product_id.name).lower():
                        order_line.update({'price_subtotal': order_line.price_unit})
