from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import calendar, logging

_logger = logging.getLogger(__name__)


class InterestBreakDown(models.TransientModel):
    _name = 'interest.breakdown.wizard'

    expected_down_payment_select = fields.Selection([('fixed','Fixed'),
                                                     ('percentage','Percentage')], string="Expected Down Payment", required=True, default='fixed')
    expected_down_payment_fixed = fields.Float(string="Fixed")
    expected_down_payment_percentage = fields.Float(string="Percentage(%)")
    no_interest_amount = fields.Float(string="Total Amount w/o Interest", readonly=True)
    interest_rate = fields.Float(string="Interest Rate(%)")
    interest_fee = fields.Float(string="Interest Fee")
    balance = fields.Float(string="Balance", compute="compute_balance")
    payment_term_id = fields.Many2one(string="Payment Terms", comodel_name="account.payment.term", readonly=True)
    payment_schedule_ids = fields.One2many(string="Payment Schedule", comodel_name="payment.schedule.wizard",
                                           inverse_name='interest_breakdown_id', readonly=True)
    add_vat = fields.Boolean(string="Add VAT")
    tax_id = fields.Many2one(string="VAT Type", comodel_name="account.tax", domain="[('type_tax_use','=','sale')]")
    vat_rate = fields.Float(string="VAT(%)", related="tax_id.amount")
    vat_type = fields.Selection([('inclusive','Inclusive'),
                                 ('exclusive','Exclusive')], string="Inclusive/Exclusive", compute="compute_vat_type",
                                help="Please see in Accounting if VAT is \'Included in Price\'.\n\nVAT Inclusive uses the Interest Fee for the Balance\nVAT Exclusive uses the VATed Interest Fee for the Balance")
    vat_amount = fields.Float(string="VAT Amount",  default=0.0, compute="compute_vat_amount")
    taxed_interest_fee = fields.Float(string="VATed Interest Fee", default=0.0, compute="compute_vat_amount")

    @api.model
    def default_get(self, vals):
        res = super(InterestBreakDown, self).default_get(vals)
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        total_interest_subtotal_fee = 0.0
        total_interest_line_tax = 0.0
        for order_line in sale_form.order_line:
            if "interest" in str(order_line.product_id.name).lower():
                total_interest_subtotal_fee += order_line.price_subtotal
                total_interest_line_tax += order_line.price_tax
        res.update({'no_interest_amount': sale_form.amount_total - total_interest_subtotal_fee - total_interest_line_tax,
                    'payment_term_id':sale_form.payment_term_id.id})
        return res

    @api.onchange('expected_down_payment_percentage')
    def onchange_fixed_down_payment(self):
        if self.expected_down_payment_percentage:
            self.expected_down_payment_fixed = self.no_interest_amount * (self.expected_down_payment_percentage/100)

    @api.onchange('interest_rate')
    def onchange_interest_fee(self):
        if self.interest_rate:
            self.interest_fee = (self.no_interest_amount - self.expected_down_payment_fixed) * (self.interest_rate/100)

    @api.depends('tax_id')
    def compute_vat_type(self):
        if self.tax_id:
            if self.tax_id.price_include:
                self.vat_type = 'inclusive'
            else:
                self.vat_type = 'exclusive'

    @api.depends('no_interest_amount','expected_down_payment_fixed','interest_fee','taxed_interest_fee')
    def compute_balance(self):
        for record in self:
            interest_fee = max(record.interest_fee, record.taxed_interest_fee)
            if record.no_interest_amount:
                record.balance = record.no_interest_amount - record.expected_down_payment_fixed + interest_fee

    @api.depends('vat_type','interest_fee')
    def compute_vat_amount(self):
        for rec in self:
            if rec.vat_type and (rec.vat_type == 'inclusive'):
                rec.vat_amount = rec.interest_fee - (rec.interest_fee * (100 / (100 + rec.vat_rate)))
                rec.taxed_interest_fee = rec.interest_fee - rec.vat_amount
            elif rec.vat_type and (rec.vat_type == 'exclusive'):
                rec.vat_amount = rec.interest_fee * (rec.vat_rate / 100)
                rec.taxed_interest_fee = rec.interest_fee + rec.vat_amount

    @api.onchange('add_vat')
    def onchange_reset_vat_computation(self):
        if not self.add_vat:
            self.tax_id = False
            self.vat_rate = 0.0
            self.vat_type = False
            self.vat_amount = 0.0
            self.taxed_interest_fee = 0.0

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
            if months == 1:
                next_date_tuple = next_date + timedelta(days=30)
            else:
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
        if len(self.payment_schedule_ids) == 0:
            raise UserError(_('Press the GENERATE button in the Schedule of Payments'))
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        interest_product = self.env['product.product'].search([('name','ilike','Interest')])
        if not interest_product:
            interest_product = self.env['product.product'].create({'name': 'Interest Fee',
                                                                   'type': 'service',
                                                                   'invoice_policy': 'order',
                                                                   'company_id': False,
                                                                   })
        interest_line_found = False
        if self.interest_fee != 0.0:
            for order_line in sale_form.order_line:
                if "interest" in str(order_line.product_id.name).lower():
                    interest_line_found = True
                    order_line.update({'price_unit': self.interest_fee,
                                       'name':order_line.name + "(edited)"})
                    if self.tax_id:
                        order_line.update({'tax_id': [(6, 0, [self.tax_id.id])]})
                    else:
                        order_line.update({'tax_id': False})
                    break
            if not interest_line_found:
                sale_form.write({'order_line':[(0,0,{'name': interest_product.name + "("+str(self.interest_rate)+"%)",
                                                     'price_unit': self.interest_fee,
                                                     'product_uom_qty': 1.0,
                                                     'order_id': sale_form.id,
                                                     'discount': 0.0,
                                                     'product_uom': interest_product.uom_id.id,
                                                     'product_id': interest_product.id,
                                                     })]
                                 })
                for order_line in sale_form.order_line:
                    if "interest" in str(order_line.product_id.name).lower() and self.tax_id:
                        order_line.update({'tax_id': [(6, 0, [self.tax_id.id])]})
        for ps_lines in sale_form.payment_schedule_ids:
            ps_lines.unlink()
        sale_form.write({'payment_schedule_ids':[(0,0,{'date': ps_lines.date,
                                                       'name': ps_lines.name,
                                                       'payments': ps_lines.payments,
                                                       'sale_order_id': ps_lines.sale_order_id.id,
                                                       })for ps_lines in self.payment_schedule_ids]
                        })
class PaymentSchedule(models.TransientModel):
    _name = 'payment.schedule.wizard'

    interest_breakdown_id = fields.Many2one(string="Interest Breakdown", comodel_name="interest.breakdown.wizard", ondelete="cascade")
    sale_order_id = fields.Many2one(string="Sale Order", comodel_name="sale.order", ondelete="cascade")
    date = fields.Date(string="Date")
    name = fields.Char(string="Description")
    payments = fields.Float(string="Payment/s")
