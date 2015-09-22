# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from datetime import datetime

class fleet_vehicle_issue_category(models.Model):
    
    _name = 'fleet.vehicle.issue.category'
    _description = 'Issue Type'
    
    name = fields.Char('Name', required=True)

class fleet_vehicle_issue(models.Model):
    
    _name = 'fleet.vehicle.issue'
    _description = 'Issue'
    _order = 'date,id DESC'
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    @api.one 
    def _get_attachment_number(self):
        '''
        returns the number of attachments attached to a record
        FIXME: not working well for classes that inherits from this
        '''
        self.attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', self._name),
                                                                        ('res_id', '=', self.id)])
    
    name = fields.Char('Subject', size=256, required=True)
    date = fields.Date('Date', required=True, default=fields.Date.today(), index=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, ondelete='cascade', index=True)
    complainant = fields.Char('Complainant')    
    category_id = fields.Many2one('fleet.vehicle.issue.category', 'Category', required=True, index=True)
    response = fields.Text('Response', required=False)
    memo = fields.Text('Description')
    
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Associated Cost', readonly=True)
    cost_amount = fields.Float('Cost Amount', readonly=True, related='cost_id.amount')
    
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', index=True, requried=True, default='1')
    date_open = fields.Date('Opened')
    date_closed = fields.Date('Closed')
    date_deadline = fields.Date('Deadline')
    state = fields.Selection([('draft', 'Draft'),
                               ('confirm', 'Confirmed'),
                               ('done', 'Resolved'),
                               ('cancel', 'Cancelled'),
                              ],
                              'State', default='draft')
    attachment_count = fields.Integer(string='Number of Attachments', compute='_get_attachment_number')
    
    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action
    
    @api.multi
    def action_log_cost(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        issue = self[0]

        compose_form = self.env.ref('fleet.fleet_vehicle_costs_form', False)        
        ctx = {
            'default_vehicle_id' : issue.vehicle_id.id,
            'default_date' : issue.date,
            'default_issue' : issue.id

        }
        return {
            'name': 'Log Associated Cost',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fleet.vehicle.cost',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'context': ctx,
        }
    
    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """

        domain = []
        if self.env['res.users'].has_group('fleet.group_fleet_user'):
            domain = [('state', '=', 'draft'), ('state', '=', 'confirmed')]
        return domain
    
    @api.multi
    def unlink(self):
        for Issue in self:
            if Issue.state not in ['draft'] and not (self.env.uid == SUPERUSER_ID):
                raise Warning('Issues that have progressed beyond "Draft" state may not be removed.')
        
        return super(fleet_vehicle_issue, self).unlink()
    
    @api.one
    def action_confirm(self):
        self.state = 'confirm'
        if not self.date_open :
            self.date_open = fields.Date.today()
    
    @api.one
    def action_done(self):
        self.state = 'done'
        self.date_closed = fields.Date.today()
          
    @api.one
    def action_cancel(self):
        self.state = 'cancel'
        self.date_closed = fields.Date.today()
    
    @api.onchange('category_id')
    def onchange_category(self):
        if self.category_id:
            self.name = self.category_id.name

class fleet_vehicle_type(models.Model):

    _name = "fleet.vehicle.type"    
    
    name = fields.Char('Name', requried=True, selectable=False)
    
class fleet_vehicle_odometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    _order = 'value desc'
    
    odo_diff = fields.Integer("Usage (km)", compute='_compute_odo_diff', store=True)

    @api.constrains('value')
    def _check_meter_value(self):
        '''
        let's ensure that odo value increases with every new one logged
        '''
        vehicle = self.vehicle_id
        # let's get the last log for this vehicle
        last_reading = self.search([('vehicle_id', '=', vehicle.id),
                                    ('id', '!=', self.id),
                                    ('date', '<=', self.date)], limit=1)
        if last_reading:
            if self.value < last_reading[0].value:
                raise ValidationError('Odometer reading can not be lesser than the last recorded odometer reading for this vehicle')
            
        return True

    @api.one
    @api.depends('value', 'vehicle_id')
    def _compute_odo_diff(self):
        # let's get the distance covered since last recorded
        odometer = self.search([('value', '<', self.value), ('vehicle_id', '=', self.vehicle_id.id)], limit=1, order='value DESC')
        if len(odometer) == 1:
            self.odo_diff = self.value - odometer[0].value
        else:
            self.odo_diff = 0
        # print '\n\n old odo diff is %d'%(self.odo_diff)

class fleet_vehicle_location(models.Model):
    
    _name = "fleet.vehicle.location"
        
    name = fields.Char('Name', required=True)

class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"
    
    
    @api.one
    @api.depends('issue_ids')
    def _get_issue_count(self):
        self.issue_count = len(self.issue_ids)
        
    @api.one
    @api.depends('gallery_ids')
    def _get_gallery_count(self):
        self.gallery_count = len(self.gallery_ids)
    
    @api.one
    def _get_odometer_date(self): 
        # TODO pls check      
        odometer_ids = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', self.id)], limit=1, order='value desc')
        if len(odometer_ids) == 0:  # we are dealing with deltas so shouldn't be doing anything if we do not have enough
            return        
        self.odometer_date = odometer_ids[0].date
        
    @api.one
    @api.depends('acquisition_date', 'podometer', 'odometer', 'cost_ids', 'cost_ids.amount')
    def _amount_vehicle(self):
        if not isinstance(self.id, int):
            return
        costpm = 0.0
        costpmon = 0.0
        costtotal = 0.0
        if len(self.odometer_ids) < 1:
            return 
        odoo_delta = self.odometer - self.odometer_ids.sorted(key=lambda r: r.value)[0].value
        if odoo_delta <= 0:
            return
        self.distance = odoo_delta
        if not len(self.cost_ids) > 0 or not self.acquisition_date:
            return
             
        time_delta = relativedelta(datetime.now(), datetime.strptime(self.acquisition_date, DATE_FORMAT))  
        # distance traveled since the first odometer was logged
                
        for cost in self.cost_ids:
            costtotal += cost.amount
        
        months = (time_delta.years * 12) + time_delta.months
        days = (months * 30) + time_delta.days
        costpmon = months and costtotal / months or costtotal
        costpm = costtotal / odoo_delta
       
        self.costpm = costpm
        self.costpmon = costpmon
        self.costtotal = costtotal        
        self.days = days
        self.lmiles = (time_delta.years > 1) and odoo_delta / time_delta.years or odoo_delta
    
        
    @api.model
    def _get_default_type(self):
        return self.env.ref('fleet_x.vehicle_type_car')
    
    @api.model
    def _get_default_location(self):
        return self.env.ref('fleet_x.vehicle_location_main')

    engine_type = fields.Char("Engine Type")
    engine_power = fields.Char("Engine Power")       
    department_id = fields.Many2one('fleet.vehicle.department', 'Department', help='Department of the vehicle', index=1, track_visibility='onchange')
    attachment_count = fields.Integer(string='Number of Attachments', compute='_get_attachment_number')
    note = fields.Text('Internal Note')   
    issue_ids = fields.One2many('fleet.vehicle.issue', 'vehicle_id', 'Issues', readonly=True)
    issue_count = fields.Integer('Issue Count', compute='_get_issue_count', readonly=True)
    gallery_ids = fields.One2many('fleet.vehicle.gallery', 'vehicle_id', 'Gallaries',
                                          readonly=True)
    gallery_count = fields.Integer('Gallery Count', compute='_get_gallery_count', readonly=True)
    odometer_date = fields.Date('Odometer Date', readonly=True, compute='_get_odometer_date', store=False)
    
    # properties
    manufacture_year = fields.Char('Year of Manufacture', size=4)
    ownership = fields.Selection([
                        ('owned', 'Owned'),
                        ('private', 'Private (owned by employee)'),
                        ('leased', 'Leased'),
                        ('rented', 'Rented'),
                        ], 'Ownership', required=False, default="owned") 
    fueltankcap = fields.Float('Fuel Tank Capacity')
    acquisition_date = fields.Date('Acquisition Date', required=True, help='Date when the vehicle has been bought', default=fields.Date.today())
    type_id = fields.Many2one('fleet.vehicle.type', 'Type')
    location_id = fields.Many2one('fleet.vehicle.location', 'Operational Location')
    
    # statistics
    lmiles = fields.Float('Miles per year', compute="_amount_vehicle", readonly=True, store=True)
    days = fields.Float('Days Since Purchase', compute="_amount_vehicle", readonly=True, store=True)
    distance = fields.Float('Distance Since Purchase', compute="_amount_vehicle", readonly=True, store=True)
    costpm = fields.Float('Cost per KM', compute="_amount_vehicle", readonly=True, store=True)
    costpmon = fields.Float('Cost per Month', compute="_amount_vehicle", readonly=True, store=True)
    costtotal = fields.Float('Total Cost', compute="_amount_vehicle", readonly=True, store=True)
    
    
    # purchase info
    ppartner = fields.Many2one('res.partner', 'Purchased From', domain="[('supplier','=',True)]")
    car_value = fields.Float('Purchase Value', help='Value of the bought vehicle') 
    podometer = fields.Integer('Odometer at Purchase')
    warrexp = fields.Date('Date', help="Expiry date for warranty of product")
    warrexpmil = fields.Integer('(or) Kilometer', help="Expiry Kilometer for warranty of product")
    active = fields.Boolean('Active', default=True, index=True)
    
    odometer_ids = fields.One2many('fleet.vehicle.odometer', 'vehicle_id', 'Odometers', readonly=1)
    cost_ids = fields.One2many('fleet.vehicle.cost', 'vehicle_id', 'Cost', readonly=1)
    
    _sql_constraints = [
        ('uniq_license_plate', 'unique(license_plate)', 'The registration # of the vehicle must be unique !'),
        ('uniq_vin', 'unique(vin_sn)', 'The Chassis # of the vehicle must be unique !')
    ]
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        vehicle = super(fleet_vehicle, self).create(vals)
        if vehicle.podometer > 0:
            self.env['fleet.vehicle.odometer'].create({
                                                'value' : vehicle.podometer,
                                                'vehicle_id' : vehicle.id
                                               })
        return vehicle
    
    @api.one 
    def _get_attachment_number(self):
        '''
        returns the number of attachments attached to a record
        FIXME: not working well for classes that inherits from this
        '''
        self.attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', self._name),
                                                                        ('res_id', '=', self.id)])

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action

        
class fleet_vehicle_model(models.Model):
    _inherit = 'fleet.vehicle.model'    
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors', domain="[('supplier','=',True)]")

# --------------
# Vehicle Department
# --------------

class fleet_vehicle_department(models.Model):

    _name = 'fleet.vehicle.department'
    
    @api.one 
    @api.depends("vehicle_ids")
    def _get_vehicle_count(self):
        '''
        '''
        self.vehicle_count = len(self.vehicle_ids)
    
#     @api.one
#     @api.depends('name')
#     def _get_dept_name(self):
#         self.complete_name = self.name
    
    @api.one 
    @api.depends('name', 'parent_id')
    def _dept_name_get_fnc(self):
        name = self.name
        if self.parent_id:
            name = self.parent_id.name + ' / ' + name
        self.display_name = name
    
    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute='_dept_name_get_fnc', string='Name', store=True)
    vehicle_ids = fields.One2many('fleet.vehicle', 'department_id', 'Vehicles')
    vehicle_count = fields.Integer('Vehicle Count', compute="_get_vehicle_count")
    parent_id = fields.Many2one('fleet.vehicle.department', 'Parent Department', select=True)
    child_ids = fields.One2many('fleet.vehicle.department', 'parent_id', 'Child Departments')
    manager_id = fields.Many2one('res.partner', 'Manager', domain=[('employee', '=', True)])
    note = fields.Text('Note')
    
    @api.multi 
    @api.depends('display_name')
    def name_get(self):
        result = []
        for department in self:
            result.append((department.id, department.display_name))
        return result
    
    @api.constrains('parent_id')
    @api.multi
    def _check_recursion(self):
        level = 100
        cr = self.env.cr
        while len(self.ids):
            cr.execute('select distinct parent_id from fleet_vehicle_department where id IN %s', (tuple(self.ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

class fleet_vehicle_gallery(models.Model):
    
    _name = 'fleet.vehicle.gallery'
    _order = "name DESC,id"
    
    name = fields.Date('Date', requried=True, default=fields.Date.today())
    vehicle_id = fields.Many2one('fleet.vehicle', requried=True, ondelete='cascade')
    
    front_view = fields.Binary('Front View', requried=True)
    left_side_view = fields.Binary('Left Side View', requried=True)
    right_side_view = fields.Binary('Right Side View', requried=True)
    rear_view = fields.Binary('Rear View', requried=True)
    odometer_view = fields.Binary('Odometer View', requried=True)
    
    
    front_view_large = fields.Binary('Front View', requried=True)
    left_side_view_large = fields.Binary('Left Side View', requried=True)
    right_side_view_large = fields.Binary('Right Side View', requried=True)
    rear_view_large = fields.Binary('Rear View', requried=True)
    odometer_view_large = fields.Binary('Odometer View', requried=True)

class fleet_vehicle_cost(models.Model):
    _inherit = 'fleet.vehicle.cost'
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res = super(fleet_vehicle_cost, self).create(vals)
        # let's search for the issue context
        if 'default_issue' in self.env.context:
            issue = self.env['fleet.vehicle.issue'].browse(self.env.context['default_issue'])
            issue.cost_id = res.id
        return res