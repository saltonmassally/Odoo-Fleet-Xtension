# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtenson - Vehicle Service management",
    'summary': "Provides more to vehicle service management",
    'author': "Salton Massally<smassally@idtlabs.sl>",
    'website': "https://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '0.1',
    'depends': ['fleet_x'],

    'data': [
        'views/fleet_service.xml',
        'views/res_config.xml',
        'data/fleet_service_data.xml',
        'reports/fleet_board_view.xml',
        'security/ir.model.access.csv'
    ],

    'installable': True

}
