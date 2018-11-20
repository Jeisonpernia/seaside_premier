from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import calendar, logging

_logger = logging.getLogger(__name__)


class AdvancePaymentInvoice(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.model
    def default_get(self, vals):
        res = super(AdvancePaymentInvoice, self).default_get(vals)
        sale_form = self.env['sale.order'].browse(self._context.get('active_id'))
        if sale_form.payment_schedule_ids:
            for ps_lines in sale_form.payment_schedule_ids:
                if "Down Payment" in ps_lines.name:
                    payment_method = 'fixed'
                    amount = ps_lines.payments
            res.update({'advance_payment_method': payment_method,
                        'amount':amount
                        })
        return res
