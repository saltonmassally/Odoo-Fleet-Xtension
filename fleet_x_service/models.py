# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta

class fleet_service_alert(models.Model):
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _name = "fleet.service.alert"
    
    _order = "date asc"
    
    @api.model
    def _get_date_scheduled(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_notice')      
        scheduled_date = datetime.now().date() + timedelta(days=value or 7)
        return fields.Date.to_string(scheduled_date)
    
    @api.model
    def _cron_update_state(self):
        res_ids = self.search([('state', '=', 'open'),
                               ('date_scheduled', '<', fields.Date.today())])
        res_ids.write({'state' : 'overdue'})
        
    @api.one
    def _set_service_id(self):
        if len(self.service_log_id):
            self.action_done()
    
    name = fields.Char('Reference', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    date = fields.Date('Create Date', required=True, default=fields.Date.today())
    date_scheduled = fields.Date('Scheduled Date', required=True, default=_get_date_scheduled)
    date_closed = fields.Date('Closed Date')
    state = fields.Selection([('open', 'Open'),
                              ('overdue', 'Overdue'),
                              ('done', 'Done'),
                              ('cancel', 'Cancel')], default='open')
    service_log_id = fields.Many2one('fleet.vehicle.log.services', 'Service Log', readonly=True, inverse='_set_service_id')
    
    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.alert.ref')  
        return super(fleet_service_alert, self).create(data)
    
    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env['res.users'].has_group('fleet_x.group_fleet_manager'):
            domain = [('state', '=', 'open')]
        return domain
    
    @api.multi 
    def action_done(self):
        for alert in self:
            if not len(alert.service_log_id):
                raise Warning('No associated service log found for this alert and so cannot mark as closed')
        self.write({'state' : 'done', 'date_closed' : fields.Date.today()})
        
    @api.multi 
    def action_cancel(self):
        self.write({'state' : 'cancel', 'date_closed' : fields.Date.today()})
        
    @api.multi
    def action_log_service(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        compose_form = self.env.ref('fleet.fleet_vehicle_log_services_form', False)
        ctx = dict(
            default_alert_id=self.id,
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
    
    def _get_default_scheduling_interval(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_interval')
        return value
    
    def _get_default_scheduling_time(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_time')
        return value
    
    def _get_default_scheduling_odometer(self):
        ir_values = self.sudo().env['ir.values']
        value = ir_values.get_default('fleet.fuel.service', 'default_repair_scheduling_odometer')
        return value
    
    @api.one 
    @api.depends('alert_ids')
    def _get_alert_count(self):
        self.alert_count = len(self.alert_ids)
    
    repair_scheduling_interval = fields.Selection([('odometer', 'Odometer'),
                                               ('time', 'Time'),
                                               ('both', 'Both')], 'Scheduling Interval', default=_get_default_scheduling_interval)
    repair_scheduling_time = fields.Integer('Interval (Mnths)', help="Interval between each servicing in months", default=_get_default_scheduling_time)
    repair_scheduling_odometer = fields.Integer('Interval (odometer)', help="Interval between each servicing in months", default=_get_default_scheduling_odometer)
    alert_ids = fields.Many2one('fleet.service.alert', 'Alerts', domain=[('state', '=', 'open')])
    alert_count = fields.Integer('Alert Count', readonly=True, compute="_get_alert_count")
    
    @api.multi 
    def schedule_services(self):
        alert_obj = self.env['fleet.service.alert']
        for vehicle in self:
            alert_obj.create({
                              'vehicle_id' : vehicle.id,
                              })
    
    
    @api.model
    def _cron_schedule_repairs(self):
        # highly inefficient improve this piece of shit
        candidate_vehicles = self.search([])
        service_obj = self.env['fleet.vehicle.log.services']
        res_ids = []
        for vehicle in candidate_vehicles:
            last_service = service_obj.search([('vehicle_id', '=', vehicle.id)], limit=1, order="date desc")
            if vehicle.repair_scheduling_interval == 'odometer':
                if last_service.odometer + vehicle.repair_scheduling_odometer < vehicle.odometer:
                    res_ids.append(vehicle.id)
            elif vehicle.repair_scheduling_interval == 'time':
                if fields.Date.from_string(last_service.date) + timedelta(months=vehicle.repair_scheduling_time) < datetime.now().date():
                    res_ids.append(vehicle.id)
            else:
                if last_service.odometer + vehicle.repair_scheduling_odometer < vehicle.odometer or fields.Date.from_string(last_service.date) + timedelta((vehicle.repair_scheduling_time * 30)) < datetime.now().date():
                    res_ids.append(vehicle.id)
        vehicles = self.env['fleet.vehicle'].browse(res_ids)
        vehicles.schedule_services()
      
class fleet_vehicle_log_services(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    
    @api.one
    def _set_alert_id(self):
        if len(self.alert_id):
            self.alert_id.service_log_id = self.id
    
    name = fields.Char('Reference', readonly=True)
    alert_id = fields.Many2one('fleet.service.alert', 'Service Alert', inverse="_set_alert_id")
    
    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.log.ref')  
        return super(fleet_vehicle_log_services, self).create(data)
