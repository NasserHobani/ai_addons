# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    transfer_history_ids = fields.One2many(
        'helpdesk.ticket.transfer.history',
        'ticket_id',
        string='Transfer History',
        readonly=True
    )
    transfer_count = fields.Integer(
        string='Transfer Count',
        compute='_compute_transfer_count',
        store=True
    )

    @api.depends('transfer_history_ids')
    def _compute_transfer_count(self):
        for ticket in self:
            ticket.transfer_count = len(ticket.transfer_history_ids)

    def action_transfer_ticket(self):
        """Open wizard to transfer ticket"""
        self.ensure_one()
        return {
            'name': 'Transfer Ticket',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
            }
        }

    def action_view_transfer_history(self):
        """View transfer history"""
        self.ensure_one()
        return {
            'name': 'Transfer History',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.transfer.history',
            'view_mode': 'tree,form',
            'domain': [('ticket_id', '=', self.id)],
            'context': {'default_ticket_id': self.id}
        }


class HelpdeskTicketTransferHistory(models.Model):
    _name = 'helpdesk.ticket.transfer.history'
    _description = 'Helpdesk Ticket Transfer History'
    _order = 'transfer_date desc'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True, ondelete='cascade')
    config_id = fields.Many2one('helpdesk.transfer.config', string='Destination Config', required=True)
    transfer_date = fields.Datetime(string='Transfer Date', default=fields.Datetime.now, required=True)
    transferred_by = fields.Many2one('res.users', string='Transferred By', default=lambda self: self.env.user, required=True)
    remote_ticket_id = fields.Integer(string='Remote Ticket ID')
    remote_ticket_url = fields.Char(string='Remote Ticket URL', compute='_compute_remote_ticket_url', store=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial')
    ], string='Status', default='success', required=True)
    notes = fields.Text(string='Notes')
    messages_transferred = fields.Integer(string='Messages Transferred', default=0)
    followers_transferred = fields.Integer(string='Followers Transferred', default=0)
    attachments_transferred = fields.Integer(string='Attachments Transferred', default=0)

    @api.depends('config_id', 'remote_ticket_id')
    def _compute_remote_ticket_url(self):
        for record in self:
            if record.config_id and record.remote_ticket_id:
                record.remote_ticket_url = f"{record.config_id.odoo_url.rstrip('/')}/web#id={record.remote_ticket_id}&model=helpdesk.ticket&view_type=form"
            else:
                record.remote_ticket_url = False
