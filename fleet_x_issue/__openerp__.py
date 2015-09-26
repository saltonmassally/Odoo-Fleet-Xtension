# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtenson Issue Mgmt",

    'summary': "Issue Management for Fleet",
    'author': "Salton Massally <smassally@idtlabs.sl>",
    'website': "http://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '0.1',
    'depends': ['fleet_x'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_issue.xml',
        'views/fleet_data.xml'
    ],

    'installable': True

}
