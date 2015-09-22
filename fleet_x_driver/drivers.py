# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import warnings
from  datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from openerp import SUPERUSER_ID


# --------------
#  Vehicle Drivers
# --------------

class fleet_driver(models.Model):

    _name = 'fleet.driver'
    _inherits = {'res.partner':'partner_id'}
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    
    @api.one
    @api.depends('previous_assignment_ids')
    def _get_assignment_count(self):
        self.previous_assignment_count = len(self.previous_assignment_ids)

    @api.one 
    def _get_attachment_number(self):
        '''
        returns the number of attachments attached to a record
        FIXME: not working well for classes that inherits from this
        '''
        self.attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', self._name),
                                                                       ('res_id', '=', self.id)])
    @api.one
    @api.depends('issue_ids')
    def _get_issue_count(self):
        self.issue_count = len(self.issue_ids)
        
    @api.one
    @api.depends('previous_assignment_ids')
    def _compute_vehicle(self):
        self.vehicle_id = None
        if len(self.previous_assignment_ids) == 0 or self.previous_assignment_ids[0].date_end:
            return
        self.vehicle_id = self.previous_assignment_ids[0].vehicle_id
    
    @api.one
    def _set_date_license_exp(self):
        if self.state == 'license_exp' and fields.Date.from_string(self.date_license_exp) > datetime.now().date():
            if len(self.vehicle_id):
                self.state = 'assigned'
            else:
                self.state = 'unassigned'
    
    partner_id = fields.Many2one('res.partner' , required=True, ondelete="cascade")
    identification_no = fields.Char('Identification #')
    date_hired = fields.Date('Hire Date', help='Date when the driver is hired', required=True, track_visibility='onchange')
    date_terminated = fields.Date('Terminated Date', help='Date when the driver is terminated from job', track_visibility='onchange', readonly=True)
    date_license_exp = fields.Date('License exp. Date', help='Date when license expires', required=False, track_visibility='onchange', inverse="_set_date_license_exp")
    dob = fields.Date('Date of Birth')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", index=1, track_visibility='onchange', readonly=True, compute="_compute_vehicle",)
    state = fields.Selection([('draft', 'Draft'),
                              ('unassigned', 'Unassigned'),
                              ('assigned', 'Assigned'),
                              ('license_exp', 'License Expired'),
                              ('terminated', 'Terminated')], 'State', default='draft', track_visibility='onchange')


    previous_assignment_ids = fields.One2many('fleet.driver.assignment', 'driver_id' , "Previous Vehicles", readonly=True)
    previous_assignment_count = fields.Integer('Assignment Count', compute='_get_assignment_count', readonly=True)

    attachment_count = fields.Integer(string='Number of Attachments', compute='_get_attachment_number')
    license_no = fields.Char('License Number', required=True)
    issue_ids = fields.One2many('fleet.vehicle.issue', 'driver_id', 'Issues', readonly=True)
    issue_count = fields.Integer('Issue Count', compute='_get_issue_count', readonly=True)
    location_id = fields.Many2one('fleet.vehicle.location', 'Operational Location', related="vehicle_id.location_id", store=True)
    
    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env['res.users'].has_group('fleet_x.group_fleet_manager'):
            domain = [('state', '=', 'license_exp')]
        return domain

    @api.model
    def _cron_drvLic_update(self):
        """
        Updating all the drivers with expired license.
        --------,
        """
        print "\n\n Executing drivers cron function "
        # usage of self not working here. api.multi required?
        driver_obj = self.env['fleet.driver']
        recs = driver_obj.search([('date_license_exp', '<=', fields.Date.today())])
        recs.write({'state' : 'license_exp'})
        return True

   
    @api.multi
    def action_unassign(self):
        vehicle_obj = self.env['fleet.vehicle']        
        for driver in self:
            driver.write({'state': 'unassigned', 'vehicle_id' : None})
            vehicle = vehicle_obj.browse(driver.vehicle_id.id)
            if vehicle.vehicle_driver_id.id == driver.id:
                vehicle.write({'vehicle_driver_id' : None})
            elif vehicle.alt_vehicle_driver_id.id == driver.id:
                vehicle.write({'alt_vehicle_driver_id' : None, })
        return True
    
    @api.multi
    def action_confirm(self):
        for driver in self:
            if len(driver.vehicle_id) > 0:
                driver.state = 'assigned'
            else:
                driver.state = 'unassigned'
            
    
    @api.multi
    def action_assign(self):
        return self.write({'state': 'assigned'})

    @api.multi
    def action_license_exp(self):
        # @TODO we ahould update the license_exp date if current is in the future
        return self.write({'state': 'license_exp'})

    @api.multi
    def action_terminate(self):
        self.action_unassign()
        return self.write({'state': 'terminated', 'date_terminated' : fields.Date.today(), 'active' : False})
    
    @api.multi
    def action_reactivate(self):
        self.action_confirm()
        return self.write({'date_terminated' : None, 'active' : True})
    
    def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
        fields_to_hide = []
        res = super(fleet_driver, self).fields_get(cr, uid, fields, context)
        for field in fields_to_hide:
            res[field]['selectable'] = False
        return res

class fleet_vehicle_cost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    type_id = fields.Many2one('fleet.vehicle.type', 'Vehicle Type', related='vehicle_id.type_id', readonly=True, store=True)
    
# --------------
# Fleet Vehicle
# --------------

class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"
    
    @api.one
    @api.depends('previous_assignment_ids')
    def _get_assignment_count(self):
        self.previous_assignment_count = len(self.previous_assignment_ids)
        
#     @api.one
#     @api.depends('previous_assignment_ids', 'previous_assignment_ids.type')
#     def _compute_driver(self):
#         assignment_obj = self.env['fleet.driver.assignment']
#         primary_drivers = assignment_obj.search( [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'primary')])
#         if len(primary_drivers):
#             self.vehicle_driver_id =  primary_drivers[0].driver_id
    
    @api.one
    @api.constrains('vehicle_driver_id', 'alt_vehicle_driver_id')
    def _check_drivers(self):
        if self.vehicle_driver_id and self.alt_vehicle_driver_id and self.vehicle_driver_id.id == self.alt_vehicle_driver_id.id:
            raise Warning('Primary and Alternate drivers can not be the same')
    
#     @api.one
#     @api.depends('previous_assignment_ids', 'previous_assignment_ids.type')
#     def _compute_alt_driver(self):
#         assignment_obj = self.env['fleet.driver.assignment']
#         secondary_drivers = assignment_obj.search( [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'secondary')])
#         if len(secondary_drivers):
#             self.alt_vehicle_driver_id =  secondary_drivers[0].driver_id

    @api.one
    def _set_driver(self):
        assignment_obj = self.env['fleet.driver.assignment']
        domain = [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'primary')]
        drivers = assignment_obj.search(domain)
        if len(self.vehicle_driver_id) == 0:
            if len(drivers) == 0:
                return
            else:
                drivers[0].date_end = fields.Date.today()  
                drivers[0].odometer_end = self.odometer  
                drivers[0].driver_id.state = 'unassigned'
            return 
        if len(drivers):
            drivers[0].date_end = fields.Date.today()  
            drivers[0].odometer_end = self.odometer 
        self.env['fleet.driver.assignment'].create({
                                                    'vehicle_id' : self.id,
                                                    'driver_id' : self.vehicle_driver_id.id,
                                                    'date_start' : fields.Date.today(),
                                                    'type' : 'primary'
                                                    })
        self.vehicle_driver_id.state = 'assigned'
        
    @api.one
    def _set_alt_driver(self):
        assignment_obj = self.env['fleet.driver.assignment']
        domain = [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'secondary')]
        drivers = assignment_obj.search(domain)
        if len(self.alt_vehicle_driver_id) == 0:
            if len(drivers) == 0:
                return
            else:
                drivers[0].date_end = fields.Date.today()  
                drivers[0].odometer_end = self.odometer
                drivers[0].driver_id.state = 'unassigned'
            return
        
        if len(drivers):
            drivers[0].date_end = fields.Date.today()  
            drivers[0].odometer_end = self.odometer 
        self.env['fleet.driver.assignment'].create({
                                                    'vehicle_id' : self.id,
                                                    'driver_id' : self.alt_vehicle_driver_id.id,
                                                    'date_start' : fields.Date.today(),
                                                    'type' : 'secondary'
                                                    })
        self.alt_vehicle_driver_id.state = 'assigned'
   
    # -- Overriding exitings driver_id field --
    # driver_id = fields.Many2one('fleet.driver', string="Current Driver", compute='_compute_current_driver', store=False)
   
    vehicle_driver_id = fields.Many2one('fleet.driver', 'Assigned Driver (Primary)', help='Primary driver of the vehicle', track_visibility='onchange', \
                                inverse="_set_driver", domain=[('state', '=', 'unassigned')])
    alt_vehicle_driver_id = fields.Many2one('fleet.driver', 'Assigned Driver (Secondary)', help='Secondary driver of the vehicle', track_visibility='onchange', \
                               inverse="_set_alt_driver", domain=[('state', '=', 'unassigned')])
    driver_id = fields.Many2one('res.partner', 'Driver', help='Driver of the vehicle', related='vehicle_driver_id.partner_id', readonly=True, required=False, store=True)
    previous_assignment_ids = fields.One2many('fleet.driver.assignment', 'vehicle_id' , "Previous Drivers", readonly=True)
    previous_assignment_count = fields.Integer(string='Assignment History', compute='_get_assignment_count', readonly=True)
    
    
   
    
    @api.multi
    def write(self, vals):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        for vehicle in self:
            changes = []
            if 'model_id' in vals and vehicle.model_id.id != vals['model_id']:
                value = self.env['fleet.vehicle.model'].browse(vals['model_id']).name
                oldmodel = vehicle.model_id.name or 'None'
                changes.append("Model: from '%s' to '%s'" % (oldmodel, value))
            if 'vehicle_driver_id' in vals and vehicle.vehicle_driver_id.id != vals['vehicle_driver_id']:
                value = self.env['fleet.driver'].browse(vals['vehicle_driver_id']).name
                olddriver = (vehicle.vehicle_driver_id.name) or 'None'
                changes.append("Driver: from '%s' to '%s'" % (olddriver, value))
            if 'state_id' in vals and vehicle.state_id.id != vals['state_id']:
                value = self.env['fleet.vehicle.state'].browse(vals['state_id']).name
                oldstate = vehicle.state_id.name or 'None'
                changes.append("State: from '%s' to '%s'" % (oldstate, value))
            if 'license_plate' in vals and vehicle.license_plate != vals['license_plate']:
                old_license_plate = vehicle.license_plate or 'None'
                changes.append("License Plate: from '%s' to '%s'" % (old_license_plate, vals['license_plate']))

            if len(changes) > 0:
                vehicle.message_post(body=", ".join(changes))

        vehicle_id = super(fleet_vehicle, self).write(vals)
        if 'vehicle_driver_id' in vals and vehicle.vehicle_driver_id.id != vals['vehicle_driver_id']:
            vehicle.vehicle_driver_id.action_assign()
        return vehicle_id
    
class fleet_x_driver_assign(models.Model):

    _name = 'fleet.driver.assignment'
    _order = 'date_start DESC, id DESC'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', requried=True)
    driver_id = fields.Many2one('fleet.driver', 'Driver', required=True)
    date_start = fields.Date('Start Date', required=True, help='Vehicle assignment start-date') 
    date_end = fields.Date('End Date', help='Vehicle assignment end-date', default=False)
    notes = fields.Text('Notes')
    odometer_start = fields.Float('Odometer at Start', readonly=True)
    odometer_end = fields.Float('Odometer at Finish', readonly=True)
    type = fields.Selection([('primary', 'Primary'), ('secondary', 'Secondary')], required=True, default='primary')

    @api.model
    @api.returns('fleet.driver.assignment')
    def create(self, data):
        res = super(fleet_x_driver_assign, self).create(data)
        res.odometer_start = res.vehicle_id.odometer
        return res

    @api.one
    @api.constrains('driver_id', 'vehicle_id')
    def _check_driver_assign(self):
        domain = [
                  ('driver_id', '=', self.driver_id.id),
                  ('id', '!=', self.id),
                  ('vehicle_id', '!=', self.vehicle_id.id),
                  '|',
                  ('date_end', 'in', (False, None)),
                  ('date_end', '>', self.date_start),
                  ]
        if self.search_count(domain):
            raise ValidationError('Driver is already assigned to another vehicle')
        
        domain = [
                  ('vehicle_id', '=', self.vehicle_id.id),
                  ('id', '!=', self.id),
                  ('driver_id', '!=', self.driver_id.id),
                  ('type', '=', self.type),
                  '|',
                  ('date_end', 'in', (False, None)),
                  ('date_end', '>', self.date_start),
                  
                  ]
        if self.search_count(domain):
            raise ValidationError('Vehicle is already assigned to another driver of this same type')

class fleet_vehicle_issue(models.Model):    
    _inherit = 'fleet.vehicle.issue'
    
    driver_id = fields.Many2one('fleet.driver', 'Responsible', required=True, readonly=True, domain=[('state', 'not in', ('draft', 'terminated'))],
                                   states={'draft': [('readonly', False)]})
