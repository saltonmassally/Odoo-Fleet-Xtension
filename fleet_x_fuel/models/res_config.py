# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _
from openerp.osv import fields, osv

class fleet_config_settings(osv.osv_memory):
    _name = 'fleet.config.settings'
    _inherit = 'fleet.config.settings'

    _columns = {
        'default_coupon_creation': fields.boolean('Automatic Coupon Creation', help="Automatically create coupons based on fueling policy"),
        'default_price_per_lt': fields.float('Fuel Price per Liter'),
        'default_efficiency_alert_buffer': fields.float('Fuel Efficiency Alert Buffer', help='Alerts managers to fuel log efficiency that if \
         this amount greater than or lesser than average'),

    }

    _defaults = {
        'default_coupon_creation' : False,
        'default_price_per_lt': 3750.00,
    }

    
    def set_default_coupon_creation(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.coupon', 'default_coupon_creation',
            config.default_coupon_creation)
  
    def get_default_coupon_creation(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        create_coupon = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.coupon', 'default_coupon_creation')
        return {'default_coupon_creation': create_coupon}
    
    def set_default_price_per_lt(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.log', 'default_price_per_lt',
            config.default_price_per_lt)
  
    def get_default_price_per_lt(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        price = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.log', 'default_price_per_lt')
        return {'default_price_per_lt': price}
    
    def set_default_efficiency_alert_buffer(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.log', 'default_efficiency_alert_buffer',
            config.default_efficiency_alert_buffer)
  
    def get_default_efficiency_alert_buffer(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        price = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.log', 'default_efficiency_alert_buffer')
        return {'default_efficiency_alert_buffer': price}
    
  

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: