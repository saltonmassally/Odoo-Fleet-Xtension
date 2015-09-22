# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.one 
    def _count_cost(self):
        self.fuel_count = self.env['fleet.vehicle.log.fuel'].search_count([('vendor_id', '=', self.id)])
        self.service_count = self.env['fleet.vehicle.log.services'].search_count([('vendor_id', '=', self.id)])
        self.contract_count = self.env['fleet.vehicle.log.contract'].search_count([('insurer_id', '=', self.id)])
    
    fuel_count = fields.Integer(compute='_count_cost', readonly=True)
    service_count = fields.Integer(compute='_count_cost', readonly=True)
    contract_count = fields.Integer(compute='_count_cost', readonly=True)


