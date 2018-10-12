from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import calendar, logging

_logger = logging.getLogger(__name__)


class InterestBreakDown(models.TransientModel):
    _name = 'interest.breakdown.wizard'

    misc_rate = fields.Float(string="Miscellaneous Rate(%)")
    product_amount = fields.Float(string="Amount", readonly=True)
    misc_fee = fields.Float(string="Miscellaneous Fee", compute="compute_misc_fee")

    expected_down_payment_select = fields.Selection([('fixed','Fixed'),
                                                     ('percentage','Percentage')], string="Expected Down Payment", required=True, default='fixed')
    expected_down_payment_fixed = fields.Float(string="Fixed", required=True)
    expected_down_payment_percentage = fields.Float(string="Percentage(%)")
    no_interest_amount = fields.Float(string="Total Amount w/o Interest", readonly=True)
    interest_rate = fields.Float(string="Interest Rate(%)")
    interest_fee = fields.Float(string="Interest Fee", compute="compute_interest_fee")
    balance = fields.Float(string="Balance", compute="compute_balance")
    payment_term_id = fields.Many2one(string="Payment Terms", comodel_name="account.payment.term", readonly=True)
    payment_schedule_ids = fields.One2many(string="Payment Schedule", comodel_name="payment.schedule.wizard",
                                           inverse_name='interest_breakdown_id', readonly=True)

    @api.model
    def default_get(self, vals):
        res = super(InterestBreakDown, self).default_get(vals)
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        gross_membership_fee = 0.0
        for order_line in sale_form.order_line:
            if order_line.product_id.membership:
                gross_membership_fee += order_line.price_subtotal
        res.update({'no_interest_amount': sale_form.amount_total,
                    'payment_term_id':sale_form.payment_term_id.id,
                    'product_amount': gross_membership_fee})
        return res

    @api.depends('misc_rate')
    def compute_misc_fee(self):
        for record in self:
            if record.misc_rate:
                record.misc_fee = record.product_amount*(record.misc_rate/100)

    @api.onchange('expected_down_payment_percentage')
    def set_fixed_down_payment(self):
        if self.expected_down_payment_percentage:
            self.expected_down_payment_fixed = self.no_interest_amount * (self.expected_down_payment_percentage/100)

    @api.depends('interest_rate')
    def compute_interest_fee(self):
        for record in self:
            if record.interest_rate:
                record.interest_fee = (record.no_interest_amount - record.expected_down_payment_fixed) * (record.interest_rate/100)

    @api.depends('no_interest_amount','expected_down_payment_fixed','interest_fee')
    def compute_balance(self):
        for record in self:
            if record.no_interest_amount:
                record.balance = record.no_interest_amount - record.expected_down_payment_fixed + record.interest_fee

    @api.multi
    def generate_payment_schedule(self):
        for current_lines in self.payment_schedule_ids:
            current_lines.unlink()
        months = self.payment_term_id.number_of_months
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        ctr = 0
        next_date = date.today().strftime('%Y-%m-%d')
        while (ctr <= months):
            if ctr == 0:
                name = "Period "+ str(ctr)+ ": Down Payment"
                payments = self.expected_down_payment_fixed
            else:
                name = "Period "+ str(ctr)+ ": Payment"
                payments = self.balance / months
            self.write({'payment_schedule_ids':[(0,0,{'date': next_date,
                                                      'name': name,
                                                      'payments': payments,
                                                      'sale_order_id': sale_form.id,
                                                      'interest_breakdown_id':self.id
                                                      })]
                        })
            next_date = datetime.strptime(next_date, '%Y-%m-%d')
            new_year = next_date.year
            new_month = next_date.month + 1
            if new_month > 12:
                new_year += 1
                new_month -= 12
            last_day_new_month = calendar.monthrange(new_year, new_month)[1]
            new_day = min(next_date.day, last_day_new_month)
            next_date_tuple = date(new_year, new_month, new_day)
            next_date = next_date_tuple.strftime('%Y-%m-%d')
            ctr += 1
        return {"type": "ir.actions.do_nothing",}

    @api.multi
    def create_interest_line(self):
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        for ps_lines in sale_form.payment_schedule_ids:
            ps_lines.unlink()
        interest_product = self.env['product.product'].search([('name','ilike','Interest')])
        misc_product = self.env['product.product'].search([('name','ilike','Misc')])
        if not misc_product:
            misc_product = self.env['product.product'].create({'name': 'Miscellaneous Fee',
                                                               'type': 'service',
                                                               'invoice_policy': 'order',
                                                               'company_id': False,
                                                               })
        if not interest_product:
            interest_product = self.env['product.product'].create({'name': 'Interest Fee',
                                                                   'type': 'service',
                                                                   'invoice_policy': 'order',
                                                                   'company_id': False,
                                                                   })
        sale_form.write({'order_line':[(0,0,{'name': misc_product.name + "("+str(self.misc_rate)+"%)",
                                             'price_unit': self.misc_fee,
                                             'product_uom_qty': 1.0,
                                             'order_id': sale_form.id,
                                             'discount': 0.0,
                                             'product_uom': misc_product.uom_id.id,
                                             'product_id': misc_product.id,
                                             }),
                                       (0,0,{'name': interest_product.name + "("+str(self.interest_rate)+"%)",
                                             'price_unit': self.interest_fee,
                                             'product_uom_qty': 1.0,
                                             'order_id': sale_form.id,
                                             'discount': 0.0,
                                             'product_uom': interest_product.uom_id.id,
                                             'product_id': interest_product.id,
                                             })],
                         'payment_schedule_ids':[(0,0,{'date': ps_lines.date,
                                                       'name': ps_lines.name,
                                                       'payments': ps_lines.payments,
                                                       'sale_order_id': ps_lines.sale_order_id.id,
                                                       })for ps_lines in self.payment_schedule_ids]
                        })
        for order_line in sale_form.order_line:
            if "interest" in str(order_line.product_id.name).lower():
                order_line.update({'price_subtotal': order_line.price_unit})
            if "misc" in str(order_line.product_id.name).lower():
                order_line.update({'price_subtotal': order_line.price_unit})

class PaymentSchedule(models.TransientModel):
    _name = 'payment.schedule.wizard'

    interest_breakdown_id = fields.Many2one(string="Interest Breakdown", comodel_name="interest.breakdown.wizard", ondelete="cascade")
    sale_order_id = fields.Many2one(string="Sale Order", comodel_name="sale.order", ondelete="cascade")
    date = fields.Date(string="Date")
    name = fields.Char(string="Description")
    payments = fields.Float(string="Payment/s")
