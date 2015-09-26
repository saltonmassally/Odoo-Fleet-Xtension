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
        'default_repair_scheduling_interval' : fields.selection([('odometer', 'Odometer'),
                                               ('time', 'Time'),
                                               ('both', 'Both')], 'Scheduling Interval'),
        'default_repair_scheduling_time' : fields.integer('Interval (Mnths)', help="Interval between each servicing in months"),
        'default_repair_scheduling_odometer' : fields.integer('Interval (Odometer)', help="Interval between each servicing in months"),
        'default_repair_scheduling_notice' : fields.integer('Notice (days)', help="How many days before date of schedule should notices be generated"),

    }

    _defaults = {
        'default_repair_scheduling_interval' : 'both',
        'default_repair_scheduling_time' : 3,
        'default_repair_scheduling_odometer' : 5000,
        'default_repair_scheduling_notice' : 7,
        
    }

    
    def set_default_repair_scheduling_interval(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_interval',
            config.default_repair_scheduling_interval)
  
    def get_default_repair_scheduling_interval(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        type = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_interval')
        return {'default_repair_scheduling_interval': type}
    
    def set_default_scheduling_time(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_time',
            config.default_repair_scheduling_time)
  
    def get_default_scheduling_time(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        interval = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_time')
        return {'default_repair_scheduling_time': interval}
    
    def set_default_repair_scheduling_odometer(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_odometer',
            config.default_repair_scheduling_odometer)
  
    def get_default_repair_scheduling_odometer(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        interval = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_odometer')
        return {'default_repair_scheduling_odometer': interval}
    
    def set_default_repair_scheduling_notice(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_notice',
            config.default_repair_scheduling_notice)
  
    def get_default_repair_scheduling_notice(self, cr, uid, fields, context=None):
        ir_values = self.pool.get('ir.values')
        interval = ir_values.get_default(cr, SUPERUSER_ID, 'fleet.fuel.service', 'default_repair_scheduling_notice')
        return {'default_repair_scheduling_notice': interval}
    
  

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: