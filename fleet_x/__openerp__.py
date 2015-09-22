# -*- coding: utf-8 -*-
{
    'name': "Fleet management Xtenson",

    'summary': """
        This is an extension of default Fleet Management module.
        It contains all the new features as listed in FM-Ledgerv 2""",

    'description': """
        Long description of module's purpose
    """,

    'author': "iDT Labs",
    'website': "idtlabs.sl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Managing vehicles and contracts',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'fleet', 'document', 'web_export_view', 'web_tree_image', 'disable_openerp_online', 'create_and_edit_many2one'],

    # always loaded
    'data': [
        'fleet_x_data.xml',
        'security/ir.model.access.csv',
        'templates.xml',
        'views/fleet_x.xml',
        'views/res_config_view.xml',
        'reports/fleet_x_board_view.xml',
        'reports/fleet_report_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
       # 'demo.xml',
    ],

    'installable': True

}
