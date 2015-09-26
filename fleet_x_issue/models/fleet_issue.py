# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools.translate import _

class fleet_vehicle_issue_category(models.Model):   
    _name = 'fleet.vehicle.issue.category'
    _description = 'Issue Type'
    
    name = fields.Char('Name', required=True)

class fleet_vehicle_issue(models.Model):    
    _name = 'fleet.vehicle.issue'
    _description = 'Issue'
    _order = 'date,id DESC'    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
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
            # from experience we want superusers to be able to delete
            if Issue.state not in ['draft'] and not (self.env.uid == SUPERUSER_ID): 
                raise Warning('Issues that have progressed beyond "Draft" state may not be removed.')        
        return super(fleet_vehicle_issue, self).unlink()
    
    @api.one
    def action_confirm(self):
        self.state = 'confirm'
        if not self.date_open:
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
    
class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"    
    
    @api.one
    @api.depends('issue_ids')
    def _get_issue_count(self):
        self.issue_count = len(self.issue_ids)
        
    issue_ids = fields.One2many('fleet.vehicle.issue', 'vehicle_id', 'Issues', readonly=True)
    issue_count = fields.Integer('Issue Count', compute='_get_issue_count', readonly=True)