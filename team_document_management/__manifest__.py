# -*- coding: utf-8 -*-
{
    'name': "Team Pacific Corporation Document Management",
    'version': '0.1',
    'sequence': 0,
    'summary': """
        Document Management System (DMS) to manage and store company documents inside Odoo properly.""",
    'author': "Alex Fernan Mercado - 10761",
    'company': 'Team Pacific Corporation',
    'maintainer': 'MIS - LOC 267',
    'support': 'mis@teamglac.com',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr', 'colored_tree_view'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/document_view.xml',
        'views/menu.xml',

    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
