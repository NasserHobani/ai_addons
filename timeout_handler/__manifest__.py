# -*- coding: utf-8 -*-
{
    'name': 'Timeout Handler',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'summary': 'Advanced timeout handling utilities for Odoo 17',
    'description': """
Timeout Handler Module
======================

This module provides utilities and decorators to handle long-running operations
and prevent timeout issues in Odoo 17.

Features:
---------
* Timeout decorators for methods
* Batch processing utilities with auto-commit
* Background job helpers
* Query monitoring and logging
* Timeout context managers
* Progress tracking for long operations

Usage:
------
Import the utilities in your custom modules to handle timeout-sensitive operations.

Example:
    from odoo.addons.timeout_handler.utils import with_timeout, batch_process
    
    @with_timeout(300)  # 5 minutes timeout
    def my_long_operation(self):
        # Your code here
        pass

Author: Odoo Timeout Investigation
License: LGPL-3
    """,
    'author': 'Odoo Timeout Investigation',
    'website': 'https://github.com/your-repo/timeout-handler',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/timeout_log_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
