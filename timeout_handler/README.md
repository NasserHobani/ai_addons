# Timeout Handler Module for Odoo 17

## Overview

This module provides comprehensive utilities for handling and monitoring timeout issues in Odoo 17. It includes decorators, context managers, batch processing tools, and logging functionality to help prevent and debug timeout problems.

## Features

- **Timeout Monitoring**: Decorators and context managers for monitoring execution time
- **Batch Processing**: Utilities for processing large datasets with automatic commits
- **Async Operations**: Helper functions for background task execution
- **Progress Tracking**: Built-in progress tracking and logging
- **Timeout Logging**: Database logging of timeout occurrences with analysis views
- **Retry Mechanisms**: Automatic retry with exponential backoff

## Installation

1. Copy the `timeout_handler` directory to your Odoo addons path
2. Update the addons list: `./odoo-bin -u all -d your_database`
3. Install the module from Apps menu

## Usage Examples

### 1. Basic Timeout Monitoring

```python
from odoo import models, api
from odoo.addons.timeout_handler.utils import with_timeout

class MyModel(models.Model):
    _name = 'my.model'
    
    @with_timeout(300)  # 5 minutes timeout
    @api.model
    def long_running_operation(self):
        # Your code here
        pass
```

### 2. Timeout Context Manager

```python
from odoo.addons.timeout_handler.utils import timeout_context

def my_method(self):
    with timeout_context(600, "Export Large Dataset"):
        # Long operation code
        data = self.prepare_export()
        self.write_to_file(data)
```

### 3. Batch Processing

```python
from odoo.addons.timeout_handler.utils import batch_process

def process_records(self):
    large_recordset = self.env['res.partner'].search([])
    
    for batch in batch_process(large_recordset, batch_size=100):
        for record in batch:
            record.calculate_something()
        # Auto-commits after each batch
```

### 4. Advanced Batch Processor

```python
from odoo.addons.timeout_handler.utils import BatchProcessor

def process_with_error_handling(self):
    processor = BatchProcessor(self.env, batch_size=50)
    records = self.env['sale.order'].search([('state', '=', 'draft')])
    
    def handle_error(record, error):
        # Custom error handling
        record.message_post(body=f"Processing failed: {error}")
    
    for batch in processor.process(records, error_handler=handle_error):
        for record in batch:
            record.action_confirm()
```

### 5. Async Operations

```python
from odoo.addons.timeout_handler.utils import async_operation

def start_background_task(self):
    def background_work(env):
        # This runs in a separate thread with its own cursor
        partners = env['res.partner'].search([('email', '!=', False)])
        for partner in partners:
            partner.send_newsletter()
    
    thread = async_operation(
        self.env, 
        self.env.uid, 
        self.env.context, 
        background_work
    )
    thread.start()
    
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'message': 'Background task started',
            'type': 'success',
        }
    }
```

### 6. Progress Tracking

```python
from odoo.addons.timeout_handler.utils import ProgressTracker

def process_with_progress(self):
    records = self.env['product.product'].search([])
    tracker = ProgressTracker(
        total_items=len(records),
        log_interval=5,  # Log every 5 seconds
        operation_name="Product Update"
    )
    
    for record in records:
        record.calculate_price()
        tracker.increment()
    
    tracker.finish()
```

### 7. Retry on Timeout

```python
from odoo.addons.timeout_handler.utils import retry_on_timeout

class MyModel(models.Model):
    _name = 'my.model'
    
    @retry_on_timeout(max_attempts=3, delay=2, backoff=2)
    def flaky_api_call(self):
        # This will retry up to 3 times with exponential backoff
        response = requests.get('https://api.example.com/data', timeout=30)
        return response.json()
```

### 8. Using the Mixin

```python
from odoo import models, api

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'timeout.monitor.mixin']
    
    def action_confirm(self):
        # Automatically monitored with 60s threshold
        monitored = self.timeout_monitored(threshold=60)
        
        @monitored
        def _confirm():
            return super(SaleOrder, self).action_confirm()
        
        return _confirm(self)
```

## Configuration

### Recommended `odoo.conf` Settings

```ini
[options]
workers = 4
limit_time_cpu = 600
limit_time_real = 1200
limit_time_real_cron = 3600
db_maxconn = 64
```

## Timeout Log Analysis

The module includes views for analyzing timeout occurrences:

1. **Timeout Logs**: Navigate to Settings → Technical → Timeout Monitoring → Timeout Logs
2. **Filter by Model/Method**: Use grouping to identify problem areas
3. **Graph View**: Visualize timeout patterns over time
4. **Pivot View**: Analyze timeouts by multiple dimensions

### Programmatic Access

```python
# Get timeout statistics
stats = self.env['timeout.log'].get_timeout_statistics(days=7)
print(f"Total timeouts: {stats['total_count']}")
print(f"Exceeded threshold: {stats['exceeded_count']}")
print(f"Average duration: {stats['avg_duration']}")

# Cleanup old logs
deleted = self.env['timeout.log'].cleanup_old_logs(days=30)
```

## Best Practices

1. **Use appropriate batch sizes**: Start with 100 and adjust based on memory/performance
2. **Commit frequently**: For large operations, commit after each batch
3. **Monitor first, optimize later**: Use logging to identify actual bottlenecks
4. **Set realistic thresholds**: Base on actual performance, not arbitrary numbers
5. **Handle errors gracefully**: Always include error handlers for batch operations
6. **Use async for truly independent tasks**: Only when the result isn't needed immediately

## Scheduled Actions

Add a cron job to cleanup old timeout logs:

```xml
<record id="ir_cron_cleanup_timeout_logs" model="ir.cron">
    <field name="name">Cleanup Timeout Logs</field>
    <field name="model_id" ref="model_timeout_log"/>
    <field name="state">code</field>
    <field name="code">model.cleanup_old_logs(days=30)</field>
    <field name="interval_number">1</field>
    <field name="interval_type">weeks</field>
    <field name="numbercall">-1</field>
</record>
```

## Troubleshooting

### High timeout occurrences
- Check database indexes
- Review query performance with PostgreSQL's `EXPLAIN ANALYZE`
- Consider archiving old data
- Increase worker resources or count

### Memory issues during batch processing
- Reduce batch size
- Ensure garbage collection with `gc.collect()` between batches
- Check `limit_memory_soft` and `limit_memory_hard` settings

### Background tasks not completing
- Check Odoo logs for exceptions
- Verify database connection limits
- Ensure proper cursor management (commit/rollback/close)

## License

LGPL-3

## Support

For issues or questions, please refer to the main documentation: `ODOO_17_TIMEOUTS.md`
