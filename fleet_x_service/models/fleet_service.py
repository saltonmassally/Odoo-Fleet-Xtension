# -*- coding: utf-8 -*-
import operator

from openerp import models, fields, api, tools, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta, date

class fleet_service_type(models.Model):
    _inherit = 'fleet.service.type'
    
    parent_id = fields.Many2one('fleet.service.type', 'Parent')
    display_name = fields.Char(compute='_service_name_get_fnc', string='Name', store=False)
    
    @api.one 
    @api.depends('name', 'parent_id')
    def _service_name_get_fnc(self):
        name = self.name
        if self.parent_id:
            name = self.parent_id.name + ' / ' + name
        self.display_name = name
    
    @api.multi 
    def name_get(self):
        result = []
        for service in self:
            result.append((service.id, service.display_name))
        return result
    
    @api.constrains('parent_id')
    @api.multi
    def _check_recursion(self):
        level = 100
        cr = self.env.cr
        while len(self.ids):
            cr.execute('select distinct parent_id from fleet_service_type where id IN %s', (tuple(self.ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    
class fleet_service_schedule(models.Model):
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _name = "fleet.service.schedule"    
    _order = "date asc"        
    
    @api.model
    def _get_date_deadline(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_notice')      
        scheduled_date = datetime.now().date() + timedelta(days=value or 10)
        return fields.Date.to_string(scheduled_date)
    
    name = fields.Char('Reference', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    date = fields.Date('Scheduled On', required=True, default=fields.Date.today())
    date_deadline = fields.Date('Deadline', required=True, default=_get_date_deadline)
    date_closed = fields.Date('Closed Date')
    state = fields.Selection([('open', 'Open'),
                              ('overdue', 'Overdue'),
                              ('done', 'Done'),
                              ('cancel', 'Cancel')], default='open')
    service_log_id = fields.Many2one('fleet.vehicle.log.services', 'Service Log', readonly=True, inverse='_set_service_id')
    note = fields.Text('Description')
    auto_generated = fields.Boolean()
    
    @api.one 
    @api.constrains('date_deadline', 'date')
    def _check_date(self):
        if self.date_deadline and self.date and \
            fields.Date.from_string(self.date_deadline) < fields.Date.from_string(self.date):
            raise Warning('Deadline cannot be before the date of creation')
        return True

    @api.model
    def _cron_update_overdue(self):
        res_ids = self.search([('state', '=', 'open'),
                               ('date_deadline', '<', fields.Date.today())])
        res_ids.write({'state' : 'overdue'})
        
    @api.one
    def _set_service_id(self):
        if len(self.service_log_id):
            self.action_done()
            
    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.schedule.ref')  
        return super(fleet_service_schedule, self).create(data)
    
    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env.user.has_group('fleet.group_fleet_user'):
            domain = [('state', '=', 'open')]
        return domain
    
    @api.multi 
    def action_done(self):
        for schedule in self:
            if not len(schedule.service_log_id):
                raise Warning('No associated service log found for this schedule and so cannot mark as closed')
            schedule.write({'state' : 'done', 'date_closed' : schedule.date_closed or fields.Date.today()})
        
    @api.multi 
    def action_cancel(self):
        for schedule in self:
            schedule.write({'state' : 'cancel', 'date_closed' : schedule.date_closed or fields.Date.today()})
        
    @api.multi
    def action_log_service(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        compose_form = self.env.ref('fleet.fleet_vehicle_log_services_form', False)
        ctx = dict(
            default_schedule_id=self.id,
            default_vehicle_id=self.vehicle_id.id,
            default_odometer=self.vehicle_id.odometer,
        )
        return {
            'name': _('Log Service History'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fleet.vehicle.log.services',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'context': ctx,
        }

class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"
    
    @api.model
    def _get_default_scheduling_interval(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_interval')
        return value or 'odometer'
    
    @api.model
    def _get_default_scheduling_time(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_time')
        return value or 3
    
    @api.model
    def _get_default_scheduling_odometer(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_odometer')
        return value or 5000

    last_service_id = fields.Many2one('fleet.vehicle.log.services', 'Last Service Log',
                                      readonly=True, store=True, compute="_compute_last_service")
    last_service_date = fields.Date('Last Serviced On', readonly=True, store=True,
                                    related='last_service_id.date')
    last_service_odometer = fields.Float('Last Service Odometer', readonly=True, store=True,
                                    related='last_service_id.odometer')
    next_service_date = fields.Date('Next Service On', readonly=True, store=True,
                                    compute='_compute_next_service_details')
    next_service_odometer = fields.Float('Next Service Odometer', readonly=True, store=True,
                                    compute='_compute_next_service_details')
    
    repair_scheduling_interval = fields.Selection([('odometer', 'Odometer'),
                                                   ('time', 'Time'),
                                                   ('both', 'Both')], 
                                                  'Scheduling Interval', 
                                                  default=_get_default_scheduling_interval)
    repair_scheduling_time = fields.Integer('Interval (Mnths)', 
                                            help="Interval between each servicing in months", 
                                            default=_get_default_scheduling_time)
    repair_scheduling_odometer = fields.Integer('Interval (odometer)', 
                                                help="Interval between each servicing in months", 
                                                default=_get_default_scheduling_odometer)
    schedule_ids = fields.Many2one('fleet.service.schedule', 'schedules', domain=[('state', '=', 'open')])
    schedule_count = fields.Integer('schedule Count', readonly=True, compute="_get_schedule_count")
    
        
    @api.one 
    @api.depends('log_services', 'log_services.vehicle_id', 'log_services.date')
    def _compute_last_service(self):
        logs = self.log_services.sorted(key=operator.itemgetter('date', 'odometer', 'id'))
        self.last_service_id =  logs and logs[-1] or False
        
    @api.one 
    @api.depends('last_service_id', 'log_services', 'repair_scheduling_time', 
                 'repair_scheduling_odometer', 'last_service_odometer')
    def _compute_next_service_details(self):
        last_date = self.last_service_date and fields.Date.from_string(self.last_service_date) or date.today()
        last_odometer = self.last_service_odometer or self.odometer
        next_dt = last_date + relativedelta(months=self.repair_scheduling_time)
        self.next_service_date = fields.Date.to_string(next_dt)
        self.next_service_odometer = last_odometer + self.repair_scheduling_odometer
        
    @api.one 
    @api.depends('schedule_ids')
    def _get_schedule_count(self):
        x = len(self.schedule_ids.filtered((lambda r: r.state in ('open', 'overdue'))))
        self.schedule_count = len(self.schedule_ids.filtered((lambda r: r.state in ('open', 'overdue'))))
    
    @api.model
    def _cron_schedule_repairs(self):
        service_obj = self.env['fleet.vehicle.log.services']
        res_ids = []        
        for vehicle in self.search([]):
            if vehicle.repair_scheduling_interval == 'odometer' and vehicle.odometer >= vehicle.next_service_odometer:
                res_ids.append(vehicle.id)
            elif vehicle.repair_scheduling_interval == 'time' \
             and fields.Date.from_string(vehicle.next_service_date) <= date.today():
                res_ids.append(vehicle.id)
            elif vehicle.repair_scheduling_interval == 'both':
                res_ids.append(vehicle.id)
        if res_ids:
            vehicles = self.browse(res_ids)
            vehicles.schedule_services()
        
    @api.multi 
    def schedule_services(self, note=None, auto=True):
        schedule_obj = self.env['fleet.service.schedule']
        for vehicle in self:
            # let's first see if we have an outstanding 
            if schedule_obj.search_count([('state', 'in', ('open',  'overdue')),
                                           ('vehicle_id', '=', vehicle.id)]):
                continue
            schedule_obj.create({
                              'vehicle_id' : vehicle.id,
                              'auto_generated' : auto,
                              'note' : note or 'Periodic Maintennace'
                              })
      
class fleet_vehicle_log_services(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    
    @api.one
    def _set_schedule_id(self):
        if len(self.schedule_id):
            self.schedule_id.service_log_id = self.id
    
    name = fields.Char('Reference', readonly=True)
    schedule_id = fields.Many2one('fleet.service.schedule', 'Service schedule', inverse="_set_schedule_id")
    
    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.log.ref')  
        return super(fleet_vehicle_log_services, self).create(data)
