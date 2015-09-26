# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtenson - Supplier Management",
    'summary': "extension of default Fleet Management module meant to provide supplier management",
    'author': "Salton Massally<smassally@idtlabs.sl>",
    'website': "http://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '0.1',
    'depends': ['fleet_x', 'fleet_x_fuel', 'fleet_x_service'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_supplier.xml',
        'reports/fleet_supplier_report_view.xml',
        'wizard/fleet_supplier_report_view.xml'
    ],

    'installable': True

}
