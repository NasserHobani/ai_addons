# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicketTransferWizard(models.TransientModel):
    _name = 'helpdesk.ticket.transfer.wizard'
    _description = 'Transfer Helpdesk Ticket Wizard'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True, readonly=True)
    config_id = fields.Many2one('helpdesk.transfer.config', string='Destination', required=True, 
                                domain=[('active', '=', True)])
    transfer_messages = fields.Boolean(string='Transfer Messages & Logs', default=True)
    transfer_followers = fields.Boolean(string='Transfer Followers', default=True)
    transfer_attachments = fields.Boolean(string='Transfer Attachments', default=True)
    close_original = fields.Boolean(string='Close Original Ticket', default=False,
                                   help='Mark the original ticket as done after transfer')
    add_transfer_note = fields.Boolean(string='Add Transfer Note', default=True,
                                      help='Add a note in the original ticket about the transfer')
    notes = fields.Text(string='Additional Notes')

    def action_transfer(self):
        """Execute the ticket transfer"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError(_('Please select a destination configuration.'))
        
        ticket = self.ticket_id
        config = self.config_id
        
        try:
            # Prepare ticket data
            ticket_data = self._prepare_ticket_data()
            
            # Create ticket on remote Odoo
            _logger.info(f'Transferring ticket {ticket.id} to {config.odoo_url}')
            remote_ticket_id = self._create_remote_ticket(ticket_data)
            
            if not remote_ticket_id:
                raise UserError(_('Failed to create ticket on remote Odoo instance.'))
            
            # Track statistics
            messages_count = 0
            followers_count = 0
            attachments_count = 0
            
            # Transfer messages if requested
            if self.transfer_messages:
                messages_count = self._transfer_messages(remote_ticket_id)
            
            # Transfer followers if requested
            if self.transfer_followers:
                followers_count = self._transfer_followers(remote_ticket_id)
            
            # Transfer attachments if requested
            if self.transfer_attachments:
                attachments_count = self._transfer_attachments(remote_ticket_id)
            
            # Create transfer history
            history = self.env['helpdesk.ticket.transfer.history'].create({
                'ticket_id': ticket.id,
                'config_id': config.id,
                'remote_ticket_id': remote_ticket_id,
                'status': 'success',
                'notes': self.notes or '',
                'messages_transferred': messages_count,
                'followers_transferred': followers_count,
                'attachments_transferred': attachments_count,
            })
            
            # Add transfer note to original ticket
            if self.add_transfer_note:
                ticket.message_post(
                    body=_(
                        'Ticket transferred to: <a href="%s">%s</a><br/>'
                        'Remote Ticket ID: %s<br/>'
                        'Messages transferred: %s<br/>'
                        'Followers transferred: %s<br/>'
                        'Attachments transferred: %s'
                    ) % (
                        history.remote_ticket_url,
                        config.name,
                        remote_ticket_id,
                        messages_count,
                        followers_count,
                        attachments_count
                    ),
                    subject='Ticket Transferred',
                    message_type='notification'
                )
            
            # Close original ticket if requested
            if self.close_original:
                # Find the done/closed stage
                done_stage = self.env['helpdesk.stage'].search([
                    ('is_close', '=', True),
                    ('team_id', '=', ticket.team_id.id)
                ], limit=1)
                if done_stage:
                    ticket.stage_id = done_stage
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Ticket transferred successfully! Remote ticket ID: %s') % remote_ticket_id,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
        except Exception as e:
            _logger.error(f'Error transferring ticket {ticket.id}: {str(e)}', exc_info=True)
            
            # Create failed transfer history
            self.env['helpdesk.ticket.transfer.history'].create({
                'ticket_id': ticket.id,
                'config_id': config.id,
                'status': 'failed',
                'notes': f'{self.notes or ""}\n\nError: {str(e)}',
            })
            
            raise UserError(_('Transfer failed: %s') % str(e))

    def _prepare_ticket_data(self):
        """Prepare ticket data for transfer"""
        ticket = self.ticket_id
        config = self.config_id
        
        data = {
            'name': ticket.name,
            'description': ticket.description or '',
            'priority': ticket.priority or '0',
        }
        
        # Add optional fields if they exist
        if ticket.partner_id:
            data['partner_name'] = ticket.partner_id.name
            data['partner_email'] = ticket.partner_id.email or ''
            data['partner_phone'] = ticket.partner_id.phone or ''
        
        # Add transfer partner configuration (child/parent)
        if config.transfer_partner_child_id:
            data['transfer_partner_child'] = {
                'name': config.transfer_partner_child_id.name,
                'email': config.transfer_partner_child_id.email or '',
                'phone': config.transfer_partner_child_id.phone or '',
            }
        
        if config.transfer_partner_parent_id:
            data['transfer_partner_parent'] = {
                'name': config.transfer_partner_parent_id.name,
                'email': config.transfer_partner_parent_id.email or '',
                'phone': config.transfer_partner_parent_id.phone or '',
            }
        
        # Add stage mapping if configured
        if ticket.stage_id:
            data['source_stage_id'] = ticket.stage_id.id
            data['source_stage_name'] = ticket.stage_id.name
        
        if ticket.user_id:
            data['assigned_user_name'] = ticket.user_id.name
        
        # Add custom fields that might exist
        optional_fields = ['ticket_type_id', 'tag_ids', 'company_id']
        for field in optional_fields:
            if hasattr(ticket, field) and ticket[field]:
                if field == 'tag_ids':
                    data['tag_names'] = [tag.name for tag in ticket.tag_ids]
                elif field == 'company_id':
                    data['company_name'] = ticket.company_id.name
                elif field == 'ticket_type_id':
                    data['ticket_type_name'] = ticket.ticket_type_id.name
        
        return data

    def _create_remote_ticket(self, ticket_data):
        """Create ticket on remote Odoo instance"""
        config = self.config_id
        
        # Prepare values for remote creation
        remote_values = {
            'name': ticket_data['name'],
            'description': ticket_data.get('description', ''),
            'priority': ticket_data.get('priority', '0'),
        }
        
        # Try to find or create partner if email provided
        if ticket_data.get('partner_email'):
            try:
                # Search for partner by email
                partner_ids = config.call_remote_method(
                    'res.partner',
                    'search',
                    args=[[('email', '=', ticket_data['partner_email'])]],
                    kwargs={'limit': 1}
                )
                
                if partner_ids:
                    remote_values['partner_id'] = partner_ids[0]
                elif ticket_data.get('partner_name'):
                    # Create partner if not found
                    partner_id = config.call_remote_method(
                        'res.partner',
                        'create',
                        args=[{
                            'name': ticket_data['partner_name'],
                            'email': ticket_data['partner_email'],
                            'phone': ticket_data.get('partner_phone', ''),
                        }]
                    )
                    remote_values['partner_id'] = partner_id
            except Exception as e:
                _logger.warning(f'Could not create/find partner: {str(e)}')
        
        # Handle transfer partner child
        if ticket_data.get('transfer_partner_child'):
            try:
                child_data = ticket_data['transfer_partner_child']
                # Search for child partner by email on remote
                child_partner_ids = config.call_remote_method(
                    'res.partner',
                    'search',
                    args=[[('email', '=', child_data['email'])]],
                    kwargs={'limit': 1}
                ) if child_data.get('email') else []
                
                if child_partner_ids:
                    remote_values['partner_id'] = child_partner_ids[0]
                elif child_data.get('name'):
                    # Create child partner if not found
                    child_partner_id = config.call_remote_method(
                        'res.partner',
                        'create',
                        args=[{
                            'name': child_data['name'],
                            'email': child_data.get('email', ''),
                            'phone': child_data.get('phone', ''),
                        }]
                    )
                    remote_values['partner_id'] = child_partner_id
            except Exception as e:
                _logger.warning(f'Could not create/find child partner: {str(e)}')
        
        # Handle transfer partner parent
        if ticket_data.get('transfer_partner_parent'):
            try:
                parent_data = ticket_data['transfer_partner_parent']
                # Search for parent partner by email on remote
                parent_partner_ids = config.call_remote_method(
                    'res.partner',
                    'search',
                    args=[[('email', '=', parent_data['email'])]],
                    kwargs={'limit': 1}
                ) if parent_data.get('email') else []
                
                if parent_partner_ids:
                    # If we have a child partner already set, set the parent relationship
                    if remote_values.get('partner_id'):
                        try:
                            config.call_remote_method(
                                'res.partner',
                                'write',
                                args=[[remote_values['partner_id']], {'parent_id': parent_partner_ids[0]}]
                            )
                        except Exception as e:
                            _logger.warning(f'Could not set parent relationship: {str(e)}')
                elif parent_data.get('name'):
                    # Create parent partner if not found
                    parent_partner_id = config.call_remote_method(
                        'res.partner',
                        'create',
                        args=[{
                            'name': parent_data['name'],
                            'email': parent_data.get('email', ''),
                            'phone': parent_data.get('phone', ''),
                        }]
                    )
                    # Set parent relationship if we have a child partner
                    if remote_values.get('partner_id'):
                        try:
                            config.call_remote_method(
                                'res.partner',
                                'write',
                                args=[[remote_values['partner_id']], {'parent_id': parent_partner_id}]
                            )
                        except Exception as e:
                            _logger.warning(f'Could not set parent relationship: {str(e)}')
            except Exception as e:
                _logger.warning(f'Could not create/find parent partner: {str(e)}')
        
        # Handle stage mapping
        if ticket_data.get('source_stage_id'):
            try:
                # Look for stage mapping in configuration
                stage_mapping = self.env['helpdesk.transfer.stage.mapping'].search([
                    ('config_id', '=', config.id),
                    ('source_stage_id', '=', ticket_data['source_stage_id'])
                ], limit=1)
                
                if stage_mapping:
                    # Search for the destination stage by name
                    remote_stage_ids = config.call_remote_method(
                        'helpdesk.stage',
                        'search',
                        args=[[('name', '=', stage_mapping.destination_stage_name)]],
                        kwargs={'limit': 1}
                    )
                    
                    if remote_stage_ids:
                        remote_values['stage_id'] = remote_stage_ids[0]
                        _logger.info(f'Mapped stage {ticket_data["source_stage_name"]} to {stage_mapping.destination_stage_name}')
                    else:
                        _logger.warning(f'Destination stage "{stage_mapping.destination_stage_name}" not found on remote system')
            except Exception as e:
                _logger.warning(f'Could not map stage: {str(e)}')
        
        # Create the ticket
        remote_ticket_id = config.call_remote_method(
            'helpdesk.ticket',
            'create',
            args=[remote_values]
        )
        
        return remote_ticket_id

    def _transfer_messages(self, remote_ticket_id):
        """Transfer messages/logs to remote ticket"""
        ticket = self.ticket_id
        config = self.config_id
        count = 0
        
        # Get all messages from the ticket
        messages = self.env['mail.message'].search([
            ('model', '=', 'helpdesk.ticket'),
            ('res_id', '=', ticket.id),
        ], order='date asc')
        
        for message in messages:
            try:
                message_data = {
                    'body': message.body or '',
                    'subject': message.subject or '',
                    'message_type': message.message_type,
                    'subtype_id': False,  # Will use default
                    'date': fields.Datetime.to_string(message.date),
                    'author_name': message.author_id.name if message.author_id else 'Unknown',
                }
                
                # Create message on remote ticket
                config.call_remote_method(
                    'helpdesk.ticket',
                    'message_post',
                    args=[remote_ticket_id],
                    kwargs={
                        'body': message_data['body'],
                        'subject': message_data['subject'],
                        'message_type': message_data['message_type'],
                    }
                )
                count += 1
            except Exception as e:
                _logger.warning(f'Failed to transfer message {message.id}: {str(e)}')
        
        return count

    def _transfer_followers(self, remote_ticket_id):
        """Transfer followers to remote ticket"""
        ticket = self.ticket_id
        config = self.config_id
        count = 0
        
        for follower in ticket.message_partner_ids:
            try:
                # Search for partner by email on remote
                if follower.email:
                    partner_ids = config.call_remote_method(
                        'res.partner',
                        'search',
                        args=[[('email', '=', follower.email)]],
                        kwargs={'limit': 1}
                    )
                    
                    if partner_ids:
                        # Add as follower
                        config.call_remote_method(
                            'helpdesk.ticket',
                            'message_subscribe',
                            args=[remote_ticket_id, partner_ids]
                        )
                        count += 1
            except Exception as e:
                _logger.warning(f'Failed to transfer follower {follower.id}: {str(e)}')
        
        return count

    def _transfer_attachments(self, remote_ticket_id):
        """Transfer attachments to remote ticket"""
        ticket = self.ticket_id
        config = self.config_id
        count = 0
        
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'helpdesk.ticket'),
            ('res_id', '=', ticket.id),
        ])
        
        for attachment in attachments:
            try:
                if not attachment.datas:
                    _logger.warning(f'Attachment {attachment.id} ({attachment.name}) has no data, skipping')
                    continue
                
                # Create attachment on remote
                # attachment.datas is already base64 encoded, pass it directly
                attachment_data = {
                    'name': attachment.name,
                    'datas': attachment.datas,
                    'res_model': 'helpdesk.ticket',
                    'res_id': remote_ticket_id,
                    'mimetype': attachment.mimetype or 'application/octet-stream',
                    'description': attachment.description or '',
                }
                
                config.call_remote_method(
                    'ir.attachment',
                    'create',
                    args=[attachment_data]
                )
                count += 1
                _logger.info(f'Successfully transferred attachment {attachment.id} ({attachment.name})')
            except Exception as e:
                _logger.error(f'Failed to transfer attachment {attachment.id} ({attachment.name}): {str(e)}')
        
        return count
