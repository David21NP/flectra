# Part of Flectra. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    FlectraHQ Inc.
#    Copyright (C) 2017-TODAY FlectraHQ Inc(<https://www.flectrahq.com>).
#
##############################################################################
{
    'name': "Automatic Database Backup To Dropbox",
    'summary': """This module allows will generate automatic backup of databases and store to dropbox""",
    'version': '3.0.1.0',
    'author': "FlectraHQ Inc, Cybrosys",
    'website': "https://flectrahq.com",
    'category': 'Tools',
    'depends': ['auto_database_backup'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/authentication_wizard_views.xml',
        'views/db_backup_configure_views.xml',
    ],
    'license': 'LGPL-3',
    'external_dependencies': {'python': ['dropbox']},
    'installable': True,
    'auto_install': False,
    'application': False,
}
