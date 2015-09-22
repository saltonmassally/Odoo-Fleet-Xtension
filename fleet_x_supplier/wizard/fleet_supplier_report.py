
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wizard_report_fleet_supplier(osv.osv_memory):

    _name = 'wizard.report.fleet.supplier'
    _description = 'Wizard that opens supplier cost logs'
    _columns = {
        'vendor_id': fields.many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]", required=True),
        'choose_date': fields.boolean('Choose a Particular Period'),
        'date_from': fields.date('Date From'),
        'date_to': fields.date('Date To'),
    }

    _defaults = {
        'choose_date': False,
        'date_to' : fields.date.today()
    }

    def open_table(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        ctx = context.copy()
        domain = [('vendor_id', '=', data['vendor_id'][0])]
        if data['choose_date']:
            from_date = data['date_from']
            to_date = data['date_to']
            domain = [('vendor_id', '=', data['vendor_id'][0]), ('date', '>=', from_date), ('date', '<=', to_date)]
        return {
            'domain': domain,
            'name': _('Cost Logs'),
            'view_type': 'form',
            'view_mode': 'tree,graph',
            'res_model': 'report.fleet.supplier',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }
