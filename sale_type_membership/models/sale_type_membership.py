from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleMembershipProductTemplate(models.Model):
    _inherit = 'product.template'

    membership = fields.Boolean(string="is a Membership Club")
    limited = fields.Boolean(string="Limited Members")
    limited_max_number = fields.Integer(string="Maximum Number of Members")
    limited_current_number = fields.Integer(string="Current Number of Members", related="sales_count")

class SaleMembershipAccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    number_of_months = fields.Integer(string="Number of Months", required=True, help="if less than a month, put '1'")

class SaleMembershipSaleOrder(models.Model):
    _inherit = 'sale.order'

    interest_fee = fields.Float(string="Interest Fee", compute="_amount_all")
    payment_schedule_ids = fields.One2many(string="Payment Schedule", comodel_name="sale.payment.schedule",
                                           inverse_name='sale_order_id', readonly=True)

    @api.depends('misc_rate')
    def compute_misc_fee(self):
        for record in self:
            if record.misc_rate:
                record.misc_fee = record.amount_untaxed*(record.misc_rate/100)

    @api.depends('order_line.price_total')
    def _amount_all(self):
        res = super(SaleMembershipSaleOrder, self)._amount_all()
        total_interest_fee = 0.0
        for order_line in self.order_line:
            if "interest" in str(order_line.product_id.name).lower():
                total_interest_fee += order_line.price_subtotal
        self.update({'interest_fee':total_interest_fee,
                    'amount_untaxed':self.amount_untaxed - total_interest_fee,
                    })
        return res

    @api.multi
    def check_limited_member(self):
        self.ensure_one()
        for order_line in self.order_line:
            product_template = order_line.product_id.product_tmpl_id
            if product_template.limited:
                if product_template.limited_max_number >= product_template.sales_count:
                    return True
                else:
                    raise UserError(_('Membership already Full!'))
            else:
                return True

    @api.multi
    def action_confirm(self):
        res = super(SaleMembershipSaleOrder, self).action_confirm()
        for order in self:
            order.check_limited_member()
        return res

class SaleMembershipSalePaymentSchedule(models.Model):
    _name = 'sale.payment.schedule'

    sale_order_id = fields.Many2one(string="Sale Order", comodel_name="sale.order", ondelete="cascade")
    date = fields.Date(string="Date")
    name = fields.Char(string="Description")
    payments = fields.Float(string="Payment/s")

class SaleMembershipAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends('origin')
    def _getPaymentSchedule(self):
        for i in self:
            if i.origin:
                i.payment_schedule_ids = [(6, 0, [sched.id for sched in self.env['sale.payment.schedule'].search([('sale_order_id.name', '=', i.origin)])])]

    payment_schedule_ids = fields.Many2many("sale.payment.schedule", 'invoice_payment_rel', string="Payment Schedule", store=True, compute="_getPaymentSchedule")
