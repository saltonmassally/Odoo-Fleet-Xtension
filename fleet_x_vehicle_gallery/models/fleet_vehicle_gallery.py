# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools.translate import _

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

class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"
    
    gallery_ids = fields.One2many('fleet.vehicle.gallery', 'vehicle_id', 'Gallaries',
                                          readonly=True)
    gallery_count = fields.Integer('Gallery Count', compute='_get_gallery_count', readonly=True)
    
    @api.one
    @api.depends('gallery_ids')
    def _get_gallery_count(self):
        self.gallery_count = len(self.gallery_ids)
        
    
    