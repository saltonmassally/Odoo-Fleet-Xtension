# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from datetime import datetime
from dateutil import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import string
import random
import operator

class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"

    fuel_coupon_ids = fields.One2many('fleet.fuel.coupon', 'vehicle_id', 'Fuel Coupons')
    fuel_coupon_count = fields.Integer('Coupon Count', readonly=True, compute='_compute_fuel_coupon_count', store=True)
    fuel_frequency = fields.Selection([('daily', 'Daily'),
                                       ('weekly', 'Weekly'),
                                       ('monthly', 'Monthly'), ], string="Fueling Frequency")
    fuel_amount = fields.Float('Fuel Amount')
    fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel'),
                                  ('electric', 'Electric'), ('hybrid', 'Hybrid')],
                                 'Fuel Type', help='Fuel Used by the vehicle', required=True, default='gasoline')
    next_coupon_issue = fields.Date('Issue Coupon on', readonly=True)
    
    km_per_lit = fields.Float(string='Km/L', compute='_compute_efficiency', readonly=True, store=True)
    
    last_fuel_id = fields.Many2one('fleet.vehicle.log.fuel', string='Last Fuel Log', readonly=True, store=True, compute='_compute_last_fuel_log')
    last_fuel_distance = fields.Float('Distance since Refuel', readonly=True, related='last_fuel_id.odometer_delta', store=True)
    last_fuel_efficiency = fields.Float('KM/L since Refuel', readonly=True, related='last_fuel_id.efficiency', store=True)
    last_fuel_date = fields.Date('Last Refuel Date', readonly=True, related='last_fuel_id.date', store=True)
    last_fuel_liter = fields.Float('Last Refuel Liters', readonly=True, related='last_fuel_id.liter', store=True)        
    
    @api.one
    @api.depends('fuel_coupon_ids')
    def _compute_fuel_coupon_count(self):
        self.fuel_coupon_count = len(self.fuel_coupon_ids)
    
    @api.one
    @api.depends('log_fuel')
    def _compute_last_fuel_log(self):
        self.last_fuel_id = len(self.log_fuel) and \
            self.log_fuel.sorted(key=operator.itemgetter('date', 'odometer', 'id'))[-1] or False

    @api.one
    @api.depends('odometer', 'log_fuel', 'log_fuel.liter')
    def _compute_efficiency(self): 
        total_liters = 0.0
        for log in self.log_fuel:
            total_liters += log.liter
        if total_liters:
            self.km_per_lit = self.distance and self.distance / total_liters or  0.0

 
    @api.model
    def cron_issue_coupon(self):
        ir_values = self.sudo().env['ir.values']
        run = ir_values.get_default('fleet.fuel.coupon', 'default_coupon_creation')
        if not run:  # we are ensuring that coupons can indeed be created programatically
            return
        domain = [
                  '|',
                  ('next_coupon_issue', '<=', fields.Date.today()),
                  ('next_coupon_issue', 'in', (False, None)),
                  ]
        vehicle_ids = self.search(domain)
        coupon_obj = self.env['fleet.fuel.coupon']
        for vehicle in vehicle_ids:
            if not vehicle.fuel_frequency or not vehicle.fuel_amount:
                continue
            if vehicle.fuel_frequency == 'daily':
                days_delta = 1
            elif vehicle.fuel_frequency == 'monthly':
                days_delta = 30
            elif vehicle.fuel_frequency == 'weekly':
                days_delta = 7
            next_issue = date.today() + relativedelta(days=days_delta)
            next_issue_str = fields.Date.to_string(next_issue)
            coupon = coupon_obj.create({
                               'auto_generated' : True,
                               'vehicle_id' : vehicle.id,
                               'fuel_type' : vehicle.fuel_type,
                               'valid_from' : fields.Date.today(),
                               'valid_to' : next_issue_str,
                               'issued_on' : fields.Date.today(),
                               'amount' : vehicle.fuel_amount,
                               
                               })
            vehicle.next_coupon_issue = next_issue_str

class fleet_fuel_coupon(models.Model):
    _name = "fleet.fuel.coupon"
    _inherit = ['ir.needaction_mixin', 'mail.thread']    
       
    name = fields.Char('Reference', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, track_visibility='onchange')
    fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')], string="Fuel Type", related="vehicle_id.fuel_type", readonly=True)
    valid_from = fields.Date('Valid From', required=True, track_visibility='onchange')
    valid_to = fields.Date('Valid To', required=True, track_visibility='onchange')
    issued_on = fields.Date('Issued On', required=True, default=fields.Date.today())
    delivered_on = fields.Date('Delivered On')
    log_fuel = fields.One2many('fleet.vehicle.log.fuel', 'coupon_id', 'Fuel Logs', readonly=True)
    amount = fields.Float('Liters', required=True)
    amount_remaining = fields.Float('Remaining Liters', compute='_compute_amount_remaning', store=True)
    note = fields.Text('Note')
    code = fields.Char('Validation Code', readonly=True, index=1)
    auto_generated = fields.Boolean('Auto generated', readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('active', 'Active'),
                              ('done', 'Done'),
                              ('expired', 'Expired'),
                              ('cancel', 'Cancelled'), ], 'State', required=True, default='draft')
    vendor_id = fields.Many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]")
    
    odometer = fields.Float(string='Odometer Value', help='Odometer measure of the vehicle at the moment of issue')
    
    
    stat_distance_delta = fields.Float('Distance since Refuel', readonly=True)
    stat_efficiency = fields.Float('KM/L since Refuel', readonly=True)
    stat_average_efficiency = fields.Float('Average KM/L', readonly=True)
    stat_last_date = fields.Date('Last Refuel Date', readonly=True)
    stat_last_liter = fields.Float('Last Refuel Liters', readonly=True)  
    
    stat_last_coupon_id = fields.Many2one('fleet.fuel.coupon', 'Last Coupon',
                                       readonly=True,)
    stat_last_coupon_state = fields.Selection([('draft', 'Draft'),
                              ('active', 'Active'),
                              ('done', 'Done'),
                              ('expired', 'Expired'),
                              ('cancel', 'Cancelled'), ], 'State', readonly=True)
    stat_last_coupon_amount_remaining = fields.Float('Remaining Liters', readonly=True)
    
    
    _sql_constraints = [('code', 'unique(code)', 'This validation code already exists')]
    
    @api.one
    @api.depends('log_fuel', 'amount')
    def _compute_amount_remaning(self):
        amount = self.amount
        for log in self.log_fuel:
            amount -= log.liter
        self.amount_remaining = amount
        return True
    
    @api.one
    @api.onchange('vehicle_id', 'odometer', 'date')
    def onchange_odometer(self):
        if self.vehicle_id:
            self.stat_last_date = self.vehicle_id.last_fuel_date
            self.stat_last_liter = self.vehicle_id.last_fuel_liter
            self.stat_average_efficiency = self.vehicle_id.km_per_lit
            
            # last coupon stats
            dt_cmp = self.issued_on and fields.Date.from_string(self.issued_on) or date.today()
            coupons = self.vehicle_id.fuel_coupon_ids \
                .filtered(lambda r: fields.Date.from_string(r.issued_on) <= dt_cmp) \
                .sorted(key=lambda r: r.issued_on)
            if len(coupons):
                self.stat_last_coupon_id = coupons[-1].id
                self.stat_last_coupon_state = coupons[-1].state
                self.stat_last_coupon_amount_remaining = coupons[-1].amount_remaining
            
        if self.vehicle_id and self.odometer:
            if self.odometer >= self.vehicle_id.odometer:
                delta = self.odometer - self.vehicle_id.odometer
                self.stat_distance_delta = delta
                if self.vehicle_id.last_fuel_liter:
                    self.stat_efficiency = delta / self.vehicle_id.last_fuel_liter
    
    
    def _generate_code(self):
        alphanum = [random.choice(string.ascii_lowercase + string.digits) for i in range(8)]
        return ''.join(alphanum)

    @api.constrains('odometer')     
    @api.one  
    def _check_odometer(self):
        if self.odometer and self.odometer < self.vehicle_id.odometer:
            raise Warning('Odometer value cannot be lesser than vehicle\'s current odometer reading')
        return True
    
    @api.constrains('amount')     
    @api.one  
    def _check_amount(self):
        if self.amount <= 0:
            raise Warning('Allocated fuel quantity should be greater than zero')
        return True
    
    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.fuel.coupon.ref')  
        data['code'] = self._generate_code()
        return super(fleet_fuel_coupon, self).create(data)
    
    @api.onchange('issued_on')
    @api.one
    def onchange_issued_on(self):
        self.valid_from = self.issued_on
    
    @api.model
    def cron_expire_coupon(self):
        coupon_ids = self.search([('state', 'in', ('draft', 'confirmed')),
                                  ('valid_to', '<', fields.Date.today())])
        coupon_ids.write({'state' : 'expired'})
        
    @api.multi
    def action_confirm(self):
        self.write({'state' : 'active'})
        
    @api.multi
    def action_done(self):
        self.write({'state' : 'done'})
        
    @api.multi
    def action_cancel(self):
        self.write({'state' : 'cancel'})
        
    @api.multi
    def action_reset(self):
        for coupon in self:
            coupon.log_fuel.unlink()
            coupon.state = 'draft'            
       
    @api.one
    def validate_coupon(self, code):
        return (code == self.code) and True or False
    
    @api.multi
    def action_log_fuel(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        coupon = self[0]
        if coupon.amount_remaining == 0:
            return
        compose_form = self.env.ref('fleet.fleet_vehicle_log_fuel_form', False)        
        fuel_log_obj = self.env['fleet.vehicle.log.fuel']
        price = fuel_log_obj._get_default_price()
        ctx = {
            'default_vehicle_id' : coupon.vehicle_id.id,
            'default_odometer' : coupon.vehicle_id.odometer,
            'default_liter' : coupon.amount_remaining,
           'default_purchaser_id' : coupon.vehicle_id.driver_id.id,
           'default_vehicle_id' : coupon.vehicle_id.id,
           'default_coupon_id' : coupon.id,
           'default_vendor_id' : coupon.vendor_id.id,
           'default_odometer': coupon.odometer,

        }
        if price:
            ctx.update(
                       {'default_amount' : price * coupon.amount}
                       )
        return {
            'name': 'Log Fuel Coupon',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fleet.vehicle.log.fuel',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'context': ctx,
        }
    
    @api.multi
    def action_print(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        return self.env['report'].get_action(self, 'fleet_x_fuel.report_fuel_coupon')
    
    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env['res.users'].has_group('fleet.group_fleet_manager'):
            domain = [('state', '=', 'draft')]
        return domain
   
class fleet_vehicle_log_fuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'
    _order = 'date desc, odometer desc, id desc'        
    
    def _get_default_price(self):
        return self.sudo().env['ir.values'].get_default('fleet.fuel.log', 'default_price_per_lt')
    
    coupon_id = fields.Many2one('fleet.fuel.coupon', 'Coupon', domain=[('state', '=', 'active')], ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]")
    price_per_liter = fields.Float('Price Per Liter', default=_get_default_price)    
  
    right_id = fields.Many2one('fleet.vehicle.log.fuel', 'Next Fuel Log', readonly=True)
    end_odometer = fields.Float('End Odometer', readonly=True, related="right_id.odometer", store=True)
    odometer_delta = fields.Float('Distance Traveled', readonly=True, compute='_get_consumption_stats', store=True)
    efficiency = fields.Float('Fuel Efficiency', readonly=True, compute='_get_consumption_stats', store=True)
    efficiency_alert = fields.Boolean('Alert', readonly=True, compute='_get_consumption_stats', store=True)
    efficiency_alert_type = fields.Selection([('under', 'Under Utilization'),
                                              ('over', 'Over Utilization')], 'Alert Type', readonly=True, compute='_get_consumption_stats', store=True)
    
    _sql_constraints = [('fleet_fuel_right_id_unique', 'unique(right_id)', 'Next fuel log in fuel log chain should be unique')]
    
    
       
    @api.one
    @api.depends('right_id')
    def _get_consumption_stats(self):
        if not isinstance(self.id, (int)) or not self.liter:
            return
        if self.end_odometer:
            self.odometer_delta = self.end_odometer - self.odometer            
        else:
            # we use the current vehicle odometer stats then
            self.odometer_delta = self.vehicle_id.odometer - self.odometer
        self.efficiency = self.odometer_delta / self.liter
                
        # let's attempt to identify outliers
        # thought process here is that we need at least five logs for this vehicle
        # to take consumption reading seriously
        if len(self.vehicle_id.log_fuel) > 5 and self.efficiency and self.vehicle_id.km_per_lit > 0:  # we need some data to get a better understanding of average km/l
            buffer = self.sudo().env['ir.values'].get_default('fleet.fuel.log', 'default_efficiency_alert_buffer')
            buffer = buffer or 5
            if self.efficiency > (self.vehicle_id.km_per_lit + buffer):
                self.efficiency_alert = True
                self.efficiency_alert_type = 'over'
            elif self.efficiency < (self.vehicle_id.km_per_lit - buffer):
                self.efficiency_alert = True
                self.efficiency_alert_type = 'under'
            else:
                self.efficiency_alert = False
    
    @api.one
    def _get_siblings(self):
        left = right = False
        left_ids = self.search([('vehicle_id', '=', self.vehicle_id.id),
                                ('date', '<=', self.date),
                                ('odometer_id.value', '<=', self.odometer),
                                ('id', '!=', self.id)], limit=1, order="date desc, odometer desc, id desc")
        right_ids = self.search([('vehicle_id', '=', self.vehicle_id.id),
                                ('date', '>=', self.date),
                                ('odometer_id.value', '>=', self.odometer),
                                ('id', '!=', self.id)], limit=1, order="date asc, odometer asc, id asc")
        if len(left_ids) > 0:
            left = left_ids[0]
        if len(right_ids) > 0:
            right = right_ids[0]  
        return left, right
        
    @api.onchange('coupon_id')
    @api.one
    def onchange_issued_on(self):
        if self.coupon_id:
            self.vehicle_id = self.coupon_id.vehicle_id  
            self.vendor_id = self.coupon_id.vendor_id 
    
    @api.one
    @api.constrains('coupon_id')
    def _check_coupon(self):
        if self.coupon_id:
            if self.liter > (self.coupon_id.amount_remaining + self.liter):
                raise Warning('Amount being logged is more than the remaining amount on the liter')  
            if self.coupon_id.vehicle_id.id != self.vehicle_id.id:
                raise Warning('Vehicle cannot be different from that for which the coupon was issued')   
        return True
    
    @api.one
    @api.constrains('odometer')
    def _check_odometer_liter(self):
        if not self.odometer or not self.odometer > 0:
            raise Warning('Please submit an odometer reading before you can proceed')
        if not self.liter or not self.liter > 0:
            raise Warning('Please submit a liter amount reading before you can proceed')
        return True    
   
    @api.one
    def _rebuild_chain(self):
        left, right = self._get_siblings()[0]
        if left:
            left.right_id = self.id
        if right:
            self.right_id = right.id
    
    @api.multi 
    def write(self, data):
        super(fleet_vehicle_log_fuel, self).write(data)
        for log in self:
            # validation not be automatically called so we are calling it 
            log._check_odometer_liter()
            if 'date' in data or 'vehicle_id' in data:
                log._rebuild_chain()
            if log.coupon_id and log.coupon_id.amount_remaining < 0:
                log.coupon_id.state = 'done'
        return True
    
    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, data):
        log = super(fleet_vehicle_log_fuel, self).create(data)
        # validation not be automatically called so we are calling it 
        log._check_odometer_liter()        
        # let's set link to the fuel log chain
        log._rebuild_chain()
        if log.coupon_id and log.coupon_id.amount_remaining <= 0:
                log.coupon_id.write({'state' : done, 'delivered_on' : log.date})
        return log
    
    @api.multi
    def unlink(self):
        for log in self:
            left, right = log._get_siblings()[0]
            if left and right:
                log.right_id = None
                left.right_id = right.id
        super(fleet_vehicle_log_fuel, self).unlink()
    

  
