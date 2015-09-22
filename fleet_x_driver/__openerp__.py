# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtension - Driver",

    'summary': """
    Driver addon for Fleet management Xtension
        """,

    'description': """
        This extension provides drivers module to FM Extension.
        It contains all the driver related features as per FM legder v2
    """,

    'author': "iDT Labs",
    'website': "idtlabs.sl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Managing vehicles and drivers',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['fleet_x'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
        'views/drivers_x.xml',
        'views/cron.xml',
        'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
       # 'demo.xml',
    ],

    'installable': True

}
