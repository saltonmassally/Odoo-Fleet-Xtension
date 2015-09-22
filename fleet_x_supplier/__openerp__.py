# -*- coding: utf-8 -*-
{
    'name': "Fleet management Xtenson - Supplier management",

    'summary': """
        This is an extension of default Fleet Management module meant to provide supplier management""",

    'author': "iDT Labs",
    'website': "idtlabs.sl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Managing vehicles and contracts',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['fleet_x', 'fleet_x_fuel', 'fleet_x_service'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_x_supplier.xml',
        'reports/fleet_supplier_report_view.xml',
        'wizard/fleet_supplier_report_view.xml'
    ],

    'installable': True

}
