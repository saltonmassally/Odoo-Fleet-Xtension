# -*- coding: utf-8 -*-
from openerp import http

# class FleetX(http.Controller):
#     @http.route('/fleet_x/fleet_x/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fleet_x/fleet_x/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('fleet_x.listing', {
#             'root': '/fleet_x/fleet_x',
#             'objects': http.request.env['fleet_x.fleet_x'].search([]),
#         })

#     @http.route('/fleet_x/fleet_x/objects/<model("fleet_x.fleet_x"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fleet_x.object', {
#             'object': obj
#         })