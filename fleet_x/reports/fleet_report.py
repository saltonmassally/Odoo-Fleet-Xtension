import time
import datetime
from dateutil.relativedelta import relativedelta

from openerp import tools
from openerp.osv import fields, osv

class report_vehicle_issue(osv.osv):
    _name = "report.vehicle.issue"
    _description = "Vehicle Issue"
    _auto = False
    _columns = {
        'id' : fields.integer('ID'),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True, readonly=True),
        'date_open': fields.date('Date Logged'),
        'category_id': fields.many2one('fleet.vehicle.issue.category', 'Issue Category', required=True, readonly=True),
        'priority' : fields.selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', index=True, requried=True, default='1'),
        'vehicle_type_id': fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=True, readonly=True),
        'category_id' : fields.many2one('fleet.vehicle.issue.category', 'Category', required=True, index=True),
        'nbr':fields.integer('Issues', readonly=True),
        'state' : fields.selection([('draft', 'Draft'),
                               ('confirm', 'Confirmed'),
                               ('done', 'Resolved'),
                               ('cancel', 'Cancelled'),
                              ],
                              'State')
    }
    _order = 'nbr desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_vehicle_issue')
        cr.execute("""
            create or replace view report_vehicle_issue as (
                select
                    min(i.id) as id,
                    i.vehicle_id as vehicle_id,
                    i.category_id as category_id,
                    i.priority as priority,
                    v.type_id as vehicle_type_id,
                    v.department_id as department_id,
                    i.date_open as date_open,
                    i.state as state,
                    count(i.*) as nbr
                from
                    fleet_vehicle_issue i
                left join
                    fleet_vehicle v on (i.vehicle_id=v.id)
                where
                    i.state in ('confirm', 'done')
                group by
                    i.vehicle_id, i.category_id, v.type_id, i.priority, v.department_id, i.date_open, i.state
            )""")

class report_vehicle_cost(osv.osv):
    _name = "report.vehicle.cost"
    _description = "Vehicle Cost"
    _auto = False
    _columns = {
        'type_id': fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=True),
        'department_id':fields.many2one('fleet.vehicle.department', 'Department', required=True),
        'amount':fields.float('Amount', readonly=True),
        'nbr':fields.integer('# of Requests', readonly=True),
        'costpmon':fields.float('Amount', readonly=True),
    }
    _order = 'amount desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_vehicle_cost')
        cr.execute("""
            create or replace view report_vehicle_cost as (
                select
                    min(c.id) as id,
                    sum(c.amount) as amount,
                    sum(v.costpmon)  as costpmon,
                    v.type_id as type_id,
                    v.department_id as department_id,
                    count(c.*) as nbr
                from
                    fleet_vehicle_cost c
                left join
                    fleet_vehicle v on (c.vehicle_id=v.id)
                where
                    v.active = 'true'
                group by
                    v.type_id, v.department_id
            )""")
      
class report_fleet_vehicle_odometer(osv.osv):
    _name = "report.fleet.vehicle.odometer"
    _description = "Vehicle Odometer report"
    _auto = False
    _columns = {
        'name' : fields.char('Name'),
        'nbr':fields.integer('# of Requests', readonly=True),
        'date': fields.date('Date'),
        'type_id': fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=True),
        'department_id':fields.many2one('fleet.vehicle.department', 'Department', required=True),
        'value': fields.integer('Usage', group_operator="sum"),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True),
    }
    _order = 'value desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_fleet_vehicle_odometer')
        cr.execute("""
            create or replace view report_fleet_vehicle_odometer as (
                select
                    min(o.id) as id,
                    sum(o.odo_diff) as value,
                    o.vehicle_id as vehicle_id,
                    o.date as date,
                    v.name as name,
                    v.type_id as type_id,
                    v.department_id as department_id,
                    count(o.*) as nbr
                from
                    fleet_vehicle_odometer o
                left join
                    fleet_vehicle v on (o.vehicle_id=v.id)
                where
                    v.active = 'true'
                group by
                    o.vehicle_id, o.date, v.name, v.type_id, v.department_id
            )""")
