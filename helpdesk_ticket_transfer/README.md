# Helpdesk Ticket Transfer Module for Odoo 17

## Overview
This module enables transferring helpdesk tickets from one Odoo instance to another, including all details, messages, followers, and attachments.

## Features
- **Complete Ticket Transfer**: Transfer all ticket details including description, priority, partner info
- **Message History**: Transfer all chatter messages and logs with timestamps
- **Followers Transfer**: Transfer all followers to the destination ticket
- **Attachments Transfer**: Transfer all file attachments
- **Multiple Destinations**: Configure multiple destination Odoo instances
- **Transfer History**: Track all transfers with detailed statistics
- **Connection Testing**: Test connection to destination Odoo before transfer
- **Flexible Options**: Choose what to transfer (messages, followers, attachments)
- **Auto-close Option**: Optionally close the original ticket after transfer
- **Partner Management**: Configure child and parent partner relationships for transfers
- **Stage Mapping**: Map source helpdesk stages to destination stages automatically

## Installation

1. Copy the `helpdesk_ticket_transfer` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Search for "Helpdesk Ticket Transfer" and install it

## Dependencies
- `helpdesk` - Odoo Helpdesk module
- `mail` - Odoo Mail module
- `requests` - Python library (usually pre-installed)

## Configuration

### 1. Setup Transfer Configuration
1. Go to **Helpdesk > Configuration > Ticket Transfer > Transfer Configurations**
2. Click **Create** to add a new destination
3. Fill in the details:
   - **Configuration Name**: A friendly name for this destination
   - **Destination Odoo URL**: Full URL of the destination Odoo instance (e.g., https://your-odoo.com)
   - **Database Name**: Database name of the destination Odoo
   - **Username/Login**: User login for authentication
   - **API Key/Password**: Password or API key for authentication
4. Click **Test Connection** to verify the configuration
5. Save the configuration

#### Partner Configuration Tab
Configure default partner relationships for transferred tickets:
- **Transfer Child Partner**: The partner that will be assigned to tickets during transfer
- **Transfer Parent Partner**: The parent company/organization for the child partner

#### Stage Mappings Tab
Map your source system stages to destination system stages:
1. Click **Add a line**
2. Select the **Source Stage** from your current system
3. Enter the exact **Destination Stage Name** as it appears in the remote system
4. Optionally add notes about the mapping
5. Use drag handle to reorder mappings

**Important**: Stage names must match exactly (case-sensitive) on the destination system.

### 2. User Permissions
- **Helpdesk User**: Can transfer tickets and view transfer history
- **Helpdesk Manager**: Full access to configurations and transfer management

## Usage

### Transferring a Ticket

1. Open a helpdesk ticket
2. Click the **Transfer Ticket** button in the header
3. In the wizard, select:
   - **Destination**: Choose the destination Odoo instance
   - **Transfer Options**:
     - ☑ Transfer Messages & Logs
     - ☑ Transfer Followers
     - ☑ Transfer Attachments
     - ☐ Close Original Ticket
     - ☑ Add Transfer Note
4. Optionally add notes about the transfer
5. Click **Transfer** to start the process

### Viewing Transfer History

- On the ticket form, you'll see a **Transfers** stat button showing the number of transfers
- Click it to view detailed transfer history
- Or go to **Helpdesk > Configuration > Ticket Transfer > Transfer History**

## Technical Details

### Models

#### `helpdesk.transfer.config`
Stores configuration for destination Odoo instances with authentication details, partner relationships, and stage mappings.

Fields:
- Connection settings (URL, database, credentials)
- `transfer_partner_child_id`: Default child partner for transfers
- `transfer_partner_parent_id`: Default parent partner for transfers
- `stage_mapping_ids`: One2many relation to stage mappings

#### `helpdesk.transfer.stage.mapping`
Maps source helpdesk stages to destination stage names.

Fields:
- `config_id`: Link to transfer configuration
- `source_stage_id`: Stage in the source system
- `destination_stage_name`: Name of the stage in the destination system
- `sequence`: Order of mappings

#### `helpdesk.ticket.transfer.history`
Records each transfer attempt with statistics and status.

#### `helpdesk.ticket.transfer.wizard`
Transient model for the transfer wizard interface.

### API Integration
The module uses Odoo's JSON-RPC API to communicate with the destination instance:
- Authentication via `/web/session/authenticate`
- Data calls via `/web/dataset/call_kw`

### Security
- API keys/passwords are stored securely in the database
- Only users with helpdesk permissions can transfer tickets
- Connection testing before actual transfer
- Error handling and logging

## Troubleshooting

### Connection Test Fails
- Verify the destination URL is correct and accessible
- Check database name, username, and password
- Ensure the destination Odoo has the helpdesk module installed
- Check network connectivity and firewall rules

### Transfer Fails
- Check the transfer history for error details
- Verify the user has proper permissions on both instances
- Check if required fields on destination match source
- Review Odoo logs for detailed error messages

### Partial Transfer
If some items fail to transfer:
- Check the transfer history for statistics
- Messages may fail if the body is too large
- Followers may not transfer if email doesn't exist on destination
- Attachments may fail if too large or corrupted

## Support
For issues or questions, please contact your system administrator or Odoo partner.

## License
LGPL-3

## Version
17.0.1.0.0 - Initial Release
