# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json


class HelpdeskTransferConfig(models.Model):
    _name = 'helpdesk.transfer.config'
    _description = 'Helpdesk Transfer Configuration'
    _order = 'name'

    name = fields.Char(string='Configuration Name', required=True)
    odoo_url = fields.Char(string='Destination Odoo URL', required=True, help='e.g., https://your-odoo-instance.com')
    database = fields.Char(string='Database Name', required=True)
    username = fields.Char(string='Username/Login', required=True)
    api_key = fields.Char(string='API Key/Password', required=True, help='User password or API key')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')
    last_test_date = fields.Datetime(string='Last Connection Test', readonly=True)
    last_test_result = fields.Char(string='Last Test Result', readonly=True)
    
    # Partner Transfer Configuration
    transfer_partner_child_id = fields.Many2one(
        'res.partner',
        string='Transfer Child Partner',
        help='Default child partner to assign when transferring tickets'
    )
    transfer_partner_parent_id = fields.Many2one(
        'res.partner',
        string='Transfer Parent Partner',
        help='Default parent partner to assign when transferring tickets'
    )
    
    # Stage Transfer Configuration
    stage_mapping_ids = fields.One2many(
        'helpdesk.transfer.stage.mapping',
        'config_id',
        string='Stage Mappings',
        help='Map source stages to destination stages'
    )

    @api.constrains('odoo_url')
    def _check_odoo_url(self):
        for record in self:
            if record.odoo_url and not record.odoo_url.startswith(('http://', 'https://')):
                raise ValidationError(_('Odoo URL must start with http:// or https://'))

    def test_connection(self):
        """Test connection to destination Odoo instance"""
        self.ensure_one()
        try:
            url = f"{self.odoo_url.rstrip('/')}/web/session/authenticate"
            payload = {
                'jsonrpc': '2.0',
                'params': {
                    'db': self.database,
                    'login': self.username,
                    'password': self.api_key,
                }
            }
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if result.get('result') and result['result'].get('uid'):
                self.last_test_date = fields.Datetime.now()
                self.last_test_result = 'Success'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection test successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = result.get('error', {}).get('data', {}).get('message', 'Authentication failed')
                self.last_test_date = fields.Datetime.now()
                self.last_test_result = f'Failed: {error_msg}'
                raise ValidationError(_('Connection failed: %s') % error_msg)
                
        except requests.exceptions.RequestException as e:
            self.last_test_date = fields.Datetime.now()
            self.last_test_result = f'Failed: {str(e)}'
            raise ValidationError(_('Connection error: %s') % str(e))
        except Exception as e:
            self.last_test_date = fields.Datetime.now()
            self.last_test_result = f'Failed: {str(e)}'
            raise ValidationError(_('Unexpected error: %s') % str(e))

    def _get_authenticated_session(self):
        """Create and authenticate a session with the destination Odoo"""
        self.ensure_one()
        session = requests.Session()
        
        # Authenticate
        url = f"{self.odoo_url.rstrip('/')}/web/session/authenticate"
        payload = {
            'jsonrpc': '2.0',
            'params': {
                'db': self.database,
                'login': self.username,
                'password': self.api_key,
            }
        }
        
        response = session.post(url, json=payload, timeout=10)
        result = response.json()
        
        if not result.get('result') or not result['result'].get('uid'):
            error_msg = result.get('error', {}).get('data', {}).get('message', 'Authentication failed')
            raise ValidationError(_('Authentication failed: %s') % error_msg)
        
        return session, result['result']['uid']

    def call_remote_method(self, model, method, args=None, kwargs=None):
        """Call a method on the remote Odoo instance"""
        self.ensure_one()
        session, uid = self._get_authenticated_session()
        
        url = f"{self.odoo_url.rstrip('/')}/web/dataset/call_kw"
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'model': model,
                'method': method,
                'args': args or [],
                'kwargs': kwargs or {},
            }
        }
        
        response = session.post(url, json=payload, timeout=30)
        result = response.json()
        
        if 'error' in result:
            error_msg = result['error'].get('data', {}).get('message', 'Unknown error')
            raise ValidationError(_('Remote call failed: %s') % error_msg)
        
        return result.get('result')


class HelpdeskTransferStageMapping(models.Model):
    _name = 'helpdesk.transfer.stage.mapping'
    _description = 'Helpdesk Transfer Stage Mapping'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'helpdesk.transfer.config',
        string='Transfer Configuration',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    source_stage_id = fields.Many2one(
        'helpdesk.stage',
        string='Source Stage',
        required=True,
        help='Stage in the source system'
    )
    destination_stage_name = fields.Char(
        string='Destination Stage Name',
        required=True,
        help='Name of the stage in the destination system'
    )
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_source_stage', 'unique(config_id, source_stage_id)',
         'Source stage must be unique per configuration!')
    ]
