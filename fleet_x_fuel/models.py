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


class fleet_vehicle_cost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    vehicle_type_id = fields.Many2one('fleet.vehicle.type', 'Vehicle Type', related='vehicle_id.type_id', readonly=True, store=True)
    vehicle_location_id = fields.Many2one('fleet.vehicle.location', 'Vehicle Location', related='vehicle_id.location_id', readonly=True, store=True)

    @api.one
    @api.depends('vehicle_id')
    def _compute_vehicle_type(self):
        # Lets grab all the fuel records prior to current record. 1 Fueling per day
        domain = [('id', '=', self.vehicle_id.id)]
        vehicle_obj = self.env['fleet.vehicle'].search(domain)

        if len(vehicle_obj) > 0:
            self.type_id = vehicle_obj.type_id.id

class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"
    
    @api.one
    @api.depends('fuel_coupon_ids')
    def _compute_fuel_coupon_count(self):
        self.fuel_coupon_count = len(self.fuel_coupon_ids)
     
    @api.one
    @api.depends('odometer', 'log_fuel')
    def _compute_kmpl_stats(self):
        if len(self.log_fuel) == 0:
            return
        if not isinstance(self.id, (int)):
            return
        # let's get our least consumption stat
        cr = self.env.cr
        query = '''
            SELECT
                c.vehicle_id, 
                %s
            FROM 
                fleet_vehicle_log_fuel l
            LEFT JOIN
                fleet_vehicle_cost c on (l.cost_id=c.id)
            WHERE 
                vehicle_id=%s GROUP BY vehicle_id
        '''
        cr.execute(query % ('min(efficiency)', self.id))
        res_ids = cr.fetchall()
        if res_ids:
            least = res_ids[0][1]
            self.km_per_lit_least = least
         
        cr.execute(query % ('max(efficiency)', self.id))
        res_ids = cr.fetchall()
        if res_ids:
            most = res_ids[0][1]
            self.km_per_lit_most = most    
    
    @api.multi    
    def _get_vehicle(self):
        res = []
        for fuel in self:
            res.append(fuel.vehicle_id.id)
        return res 
    
    @api.one
    @api.depends('log_fuel')
    def _compute_last_fuel_log(self):
        if len(self.log_fuel):
            self.last_fuel_id = self.log_fuel.sorted(key=operator.itemgetter('date', 'odometer', 'id'))[-1].id

        
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
    
    km_per_lit = fields.Float(string='Km/L', compute='_compute_fuel_stats', readonly=True, store=True)
    fuel_litres_amount = fields.Integer(string='Total Fuel (Litres)', compute='_compute_fuel_stats', readonly=True, store=True)
    fuel_litres_cost = fields.Float(string='Total Fuel (Leones)', compute='_compute_fuel_stats', readonly=True, store=True)
     
    last_fuel_distance = fields.Float('Distance since Refuel', readonly=True, related='last_fuel_id.odometer_delta', store=True)
    last_fuel_efficiency = fields.Float('KM/L since Refuel', readonly=True, related='last_fuel_id.efficiency', store=True)
    last_fuel_date = fields.Date('Last Refuel Date', readonly=True, related='last_fuel_id.date', store=True)
    last_fuel_liter = fields.Float('Last Refuel Liters', readonly=True, related='last_fuel_id.liter', store=True)    
    last_fuel_id = fields.Many2one('fleet.vehicle.log.fuel', string='Last Fuel Log', readonly=True, store=True, compute='_compute_last_fuel_log')
    

    @api.one
    @api.depends('odometer', 'log_fuel')
    def _compute_fuel_stats(self): 
        # TODO pls check      
        self.km_per_lit = 0.0
        self.fuel_litres_amount = 0
        self.fuel_litres_cost = 0.0
        
        if not isinstance(self.id, int):
            return
        sql = '''
        SELECT count(f.id), sum(f.cost_amount), sum(f.liter), sum(c.amount) 
FROM fleet_vehicle_log_fuel as f
LEFT JOIN fleet_vehicle_cost as c on f.cost_id=c.id
WHERE c.vehicle_id=%s;
        ''' % (self.id)
        cr = self.env.cr
        cr.execute(sql)
        res = cr.fetchall()
        if res:
            self.fuel_litres_amount = res[0][0]
            self.fuel_litres_cost = res[0][1]
            total_liters = res[0][2]
        if self.distance and len(self.log_fuel) > 0:  # we are dealing with deltas so shouldn't be doing anything if we do not have enough  
            self.km_per_lit = self.distance / total_liters

 
    @api.model
    def cron_issue_coupon(self):
        ir_values = self.sudo().env['ir.values']
        run = ir_values.get_default('fleet.fuel.coupon', 'default_coupon_creation')
        if not run:
            return
        domain = [
                  ('fuel_type', 'in', ('gasoline', 'diesel')),
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
            else:
                days_delta = 7
            next_issue = datetime.now() + relativedelta(days=days_delta)
            next_issue_str = next_issue.date().strftime(DATE_FORMAT)
            coupon = coupon_obj.create({
                               'auto_generated' : True,
                               'vehicle_id' : vehicle.id,
                               'fuel_type' : vehicle.fuel_type,
                               'valid_from' : fields.Date.today(),
                               'valid_to' : next_issue_str,
                               'issued_on' : fields.Date.today(),
                               'amount' : vehicle.fuel_amount,
                               
                               })
            coupon.action_confirm()
            vehicle.next_coupon_issue = next_issue_str

   
class fleet_fuel_coupon(models.Model):
    _name = "fleet.fuel.coupon"
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    
    @api.one
    @api.depends('log_fuel', 'amount')
    def _compute_amount_remaning(self):
        amount = self.amount
        for log in self.log_fuel:
            amount -= log.liter
        self.amount_remaining = amount
        return True
    
    name = fields.Char('Reference', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')], string="Fuel Type", related="vehicle_id.fuel_type", readonly=True)
    valid_from = fields.Date('Valid From', required=True)
    valid_to = fields.Date('Valid To', required=True)
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
    
    
    
    _sql_constraints = [('code', 'unique(code)', 'This validation code already exists')]
    
    @api.onchange('vehicle_id', 'odometer')
    def onchange_odometer(self):
        if self.vehicle_id:
            self.stat_last_date = self.vehicle_id.last_fuel_date
            self.stat_last_liter = self.vehicle_id.last_fuel_liter
            self.stat_average_efficiency = self.vehicle_id.km_per_lit
            
        if self.vehicle_id and self.odometer:
            if self.odometer >= self.vehicle_id.odometer:
                delta = self.odometer - self.vehicle_id.odometer
                self.stat_distance_delta = delta
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
        if self.issued_on:
            self.valid_from = self.issued_on
    
    @api.model
    def cron_expire_coupon(self):
        coupon_ids = self.search([('state', 'in', ('draft', 'confirmed')), ('valid_to', '<', fields.Date.today())])
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
    def print_coupon(self):
        pass
    
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
    _order = 'date desc'  
        
    def _get_default_price(self):
        return self.sudo().env['ir.values'].get_default('fleet.fuel.log', 'default_price_per_lt')
       
    @api.one
    @api.depends('right_id')
    def _get_consumption_stats(self):
        if not self.liter:
            return
        if not isinstance(self.id, (int)):
            return
        if self.end_odometer:
            self.odometer_delta = self.end_odometer - self.odometer            
        else:
            # we use the current vehicle odometer stats then
            self.odometer_delta = self.vehicle_id.odometer - self.odometer
        self.efficiency = self.odometer_delta / self.liter
        
        # let's attempt to identify outliers
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
    def _get_siblings(self):
        left = right = False
        left_ids = self.search([('vehicle_id', '=', self.vehicle_id.id),
                                ('date', '<=', self.date),
                                ('odometer_id.value', '<=', self.odometer),
                                ('id', '!=', self.id)], limit=1, order="date desc")
        right_ids = self.search([('vehicle_id', '=', self.vehicle_id.id),
                                ('date', '>=', self.date),
                                ('odometer_id.value', '>=', self.odometer),
                                ('id', '!=', self.id)], limit=1, order="date asc")
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
                raise ValidationError('Amount being logged id more than the remaining amount on the liter')  
            if self.coupon_id.vehicle_id.id != self.vehicle_id.id:
                    raise ValidationError('Vehicle cannot be different from that for which the coupon is assigned')   
        return True
    
    @api.one
    @api.constrains('odometer')
    def _check_odometer_liter(self):
        if not self.odometer or not self.odometer > 0:
            raise ValidationError('Please submit an odometer reading before you can proceed')
        if not self.liter or not self.liter > 0:
            raise ValidationError('Please submit a liter amount reading before you can proceed')
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
                log.coupon_id.state = 'done'
        return log
    
    @api.multi
    def unlink(self):
        for log in self:
            left, right = log._get_siblings()[0]
            if left and right:
                log.right_id = None
                left.right_id = right.id
        super(fleet_vehicle_log_fuel, self).unlink()
    

  
