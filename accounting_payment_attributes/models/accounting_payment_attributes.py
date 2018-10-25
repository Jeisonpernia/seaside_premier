from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class PaymentAttributeAccountPayment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection([('draft', 'Draft'),
                              ('cleared','Cleared'),
                              ('posted', 'Posted'),
                              ('sent', 'Sent'),
                              ('reconciled', 'Reconciled'),
                              ('cancelled', 'Cancelled')], readonly=True, default='draft',
                             copy=False, string="Status", help="Cleared is only for Customer-related Transactions")

    post_button_filter = fields.Boolean(string="filter Post Button", compute="set_post_button_filter")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    bank_name = fields.Char(string="Bank Name")
    cheque_date_received = fields.Date(string="Cheque Date Received", help="For Customer Payments Only")
    cheque_date_cleared = fields.Date(string="Cheque Date Cleared", help="For Customer Payments Only")
    payment_journal_type = fields.Char(string="Type of Payment Journal", compute="set_payment_journal_type")

    probationary_receipt_number = fields.Char(string="Probationary Receipt Number")
    acknowledgement_receipt_number = fields.Char(string="Acknowledgment Receipt Number")
    official_receipt_number = fields.Char(string="Official Receipt Number")

    @api.depends('journal_id')
    def set_payment_journal_type(self):
        for record in self:
            record.payment_journal_type = record.journal_id.type

    @api.multi
    def _get_move_vals(self, journal=None):
        res = super(PaymentAttributeAccountPayment, self)._get_move_vals()
        res.update({'probationary_receipt_number':self.probationary_receipt_number,
                    'acknowledgement_receipt_number':self.acknowledgement_receipt_number,
                    'official_receipt_number':self.official_receipt_number,
                    'payment_journal_type':self.payment_journal_type,
                    'cheque_number':self.cheque_number,
                    'cheque_date':self.cheque_date,
                    'bank_name':self.bank_name,
                    'cheque_date_received':self.cheque_date_received,
                    'cheque_date_cleared':self.cheque_date_cleared
                    })
        return res

    @api.depends('partner_type','state','journal_id')
    def set_post_button_filter(self):
        if self.partner_type == 'customer' and self.payment_journal_type == 'bank':
            if self.state in ['draft','posted']:
                self.post_button_filter = True
            elif self.state == 'cleared':
                self.post_button_filter = False
        elif self.state == 'posted':
            self.post_button_filter = True
        else:
            self.post_button_filter = False

    @api.multi
    def customer_clear(self):
        if self.amount <= 0.00:
            raise UserError(_("Amount should be a positive value"))
        if not self.cheque_date_received:
            raise UserError(_("Cheque Date Received should be filled"))
        if not self.cheque_date_cleared:
            raise UserError(_("Cheque Date Cleared should be filled"))
        else:
            self.write({'state': 'cleared'})

    @api.multi
    def post(self):
        """ This is a copy-pasted overriden version of post() function existing in the account.payment model.
            Changes are on the rec.state if-condition.
        """
        for rec in self:
            # if rec.state != 'draft':
            #     raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name})
        return True




class PaymentAttributeAccountMove(models.Model):
    _inherit = 'account.move'

    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    bank_name = fields.Char(string="Bank Name")
    cheque_date_received = fields.Date(string="Cheque Date Received", help="For Customer Payments Only")
    cheque_date_cleared = fields.Date(string="Cheque Date Cleared", help="For Customer Payments Only")
    payment_journal_type = fields.Char(string="Type of Payment Journal")

    probationary_receipt_number = fields.Char(string="Probationary Receipt Number")
    acknowledgement_receipt_number = fields.Char(string="Acknowledgment Receipt Number")
    official_receipt_number = fields.Char(string="Official Receipt Number")
