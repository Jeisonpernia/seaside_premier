from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleRequirementsSaleOrder(models.Model):
    _inherit = 'sale.order'

    checklist = fields.Boolean(string="Enable Checklist")
    checklist_progress = fields.Float(string="Supplemented", compute="compute_checklist_progress")
    product_ids = fields.Many2many(string="Products in Order Line", comodel_name="product.product",
                                   compute="populate_product_ids")
    checklist_ids = fields.Many2many(string="Requirements", comodel_name="sale.checklist.items",
                                     domain="['|',('product_ids','in',product_ids),('always_required','=',True)]")

    @api.depends('checklist_ids')
    def compute_checklist_progress(self):
        for record in self:
            total_len = self.env['sale.checklist.items'].search_count([])
            cl_len = len(record.checklist_ids)
            if total_len != 0:
                record.checklist_progress = (cl_len * 100) / total_len

    @api.depends('order_line')
    def populate_product_ids(self):
        for rec in self:
            product_list = []
            for order_line in rec.order_line:
                if order_line.product_id.membership:
                    product_list.append(order_line.product_id.id)
            rec.product_ids = [(6, 0, product_list)]

    @api.multi
    def action_confirm(self):
        res = super(SaleRequirementsSaleOrder, self).action_confirm()
        if self.checklist:
            if self.checklist_progress == 100:
                return res
            else:
                raise UserError(_('Insufficient Supplemented Requirements'))
        return res

class SaleRequirementsSaleChecklistItems(models.Model):
    _name = 'sale.checklist.items'

    name = fields.Char(string="Item", required=True)
    description = fields.Text(string="Description")
    always_required = fields.Boolean(string="Always Required", default=True)
    product_ids = fields.Many2many(string="Membership where this is Required", comodel_name="product.product",
                                  domain="[('membership','=',True)]")
    # model_id = fields.Many2one(string="Model ID", comodel_name="ir.model")
