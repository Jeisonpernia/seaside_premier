from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleRecordAccessResPartner(models.Model):
    _inherit = 'res.partner'

    allow_salesperson = fields.Many2many(string="Allow Salespersons", comodel_name="res.users")

    @api.onchange('user_id')
    def onchange_allow_salesperson(self):
        if self.user_id:
            self.allow_salesperson = self.user_id
