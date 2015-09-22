# -*- coding: utf-8 -*-
{
    'name': "Fleet management Xtenson - Service management",

    'summary': """
        This is an extension of default Fleet Management module meant to provide more comprehensive service management""",

    'description': """
        This is an extension of default Fleet Management module meant to provide more comprehensive service management
    """,

    'author': "iDT Labs",
    'website': "idtlabs.sl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Managing vehicles and contracts',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['fleet_x'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/fleet_x_service.xml',
        'views/cron.xml',
        'views/res_config_views.xml',
        'fleet_x_service_data.xml',
        'reports/fleet_x_board_view.xml',
        'security/ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'demo': [
       # 'demo.xml',
    ],

    'installable': True

}
