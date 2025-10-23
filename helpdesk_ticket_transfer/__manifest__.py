# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Ticket Transfer',
    'version': '17.0.1.0.0',
    'category': 'Helpdesk',
    'summary': 'Transfer helpdesk tickets to another Odoo instance with all details, logs, and followers',
    'description': """
        Helpdesk Ticket Transfer
        ========================
        This module allows you to transfer helpdesk tickets to another Odoo instance.
        
        Features:
        ---------
        * Transfer complete ticket details
        * Transfer message logs and chatter history
        * Transfer followers
        * Configure multiple destination Odoo instances
        * Secure API authentication
        * Transfer history tracking
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['helpdesk', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_transfer_config_views.xml',
        'wizard/helpdesk_ticket_transfer_wizard_views.xml',
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
