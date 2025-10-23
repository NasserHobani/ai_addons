# Odoo 17 Timeout Issues - Investigation & Solutions

## Overview
This document provides comprehensive information about timeout issues in Odoo 17 and their solutions.

## Common Timeout Scenarios

### 1. HTTP Request Timeouts
**Symptoms:**
- 504 Gateway Timeout errors
- Requests failing after 60-120 seconds
- Long-running reports or exports timing out

**Causes:**
- Default proxy/nginx timeout too low
- Long-running operations (reports, imports, exports)
- Database queries taking too long

### 2. Worker Timeouts
**Symptoms:**
- Workers being killed during long operations
- "WorkerLostError" in logs
- Interrupted background jobs

**Causes:**
- `limit_time_cpu` and `limit_time_real` too restrictive
- Complex computations or batch operations

### 3. Database Timeouts
**Symptoms:**
- "statement timeout" errors
- Slow queries being terminated
- Connection pool exhaustion

**Causes:**
- Missing database indexes
- Complex queries on large datasets
- Insufficient `db_maxconn` setting

### 4. XML-RPC/JSON-RPC Timeouts
**Symptoms:**
- API calls timing out
- External integrations failing
- Mobile app connection issues

**Causes:**
- Network latency
- Heavy API operations
- Default socket timeout

## Solutions

### Odoo Configuration (`odoo.conf`)

```ini
[options]
# Worker settings
workers = 4
max_cron_threads = 2

# Timeout limits (in seconds)
limit_time_cpu = 600          # CPU time limit per request (default: 60)
limit_time_real = 1200        # Real time limit per request (default: 120)
limit_time_real_cron = 3600   # Cron job time limit (default: -1 unlimited)

# Memory limits (in bytes)
limit_memory_soft = 2147483648  # 2GB soft limit
limit_memory_hard = 2684354560  # 2.5GB hard limit

# Database connection pool
db_maxconn = 64
db_maxconn_gevent = 100

# Request limits
limit_request = 8192
```

### Nginx Configuration

```nginx
upstream odoo {
    server 127.0.0.1:8069;
}

upstream odoochat {
    server 127.0.0.1:8072;
}

server {
    listen 80;
    server_name your-domain.com;

    # Timeout settings
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    send_timeout 600s;
    
    # Buffer settings
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;
    
    # Upload size
    client_max_body_size 100M;
    client_body_timeout 600s;

    location / {
        proxy_pass http://odoo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /longpolling {
        proxy_pass http://odoochat;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Apache Configuration

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    # Timeout settings
    Timeout 600
    ProxyTimeout 600
    
    ProxyPreserveHost On
    
    <Location />
        ProxyPass http://localhost:8069/ timeout=600
        ProxyPassReverse http://localhost:8069/
    </Location>
    
    <Location /longpolling>
        ProxyPass http://localhost:8072/ timeout=600
        ProxyPassReverse http://localhost:8072/
    </Location>
</VirtualHost>
```

### PostgreSQL Configuration

Add to `postgresql.conf`:

```ini
# Connection settings
max_connections = 200
shared_buffers = 256MB

# Query timeout (in milliseconds)
statement_timeout = 300000  # 5 minutes

# Lock timeout
lock_timeout = 60000  # 1 minute

# Idle transaction timeout
idle_in_transaction_session_timeout = 600000  # 10 minutes
```

### Python Code Solutions

#### 1. Using `@api.model` with timeout handling

```python
from odoo import models, api
from odoo.exceptions import UserError
import signal
import contextlib

class TimeoutException(Exception):
    pass

@contextlib.contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Operation timed out")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class YourModel(models.Model):
    _name = 'your.model'
    
    @api.model
    def long_running_operation(self):
        try:
            with timeout(300):  # 5 minutes timeout
                # Your long-running code here
                pass
        except TimeoutException:
            raise UserError("Operation took too long and was cancelled")
```

#### 2. Using database cursor with autocommit

```python
from odoo import models, api

class YourModel(models.Model):
    _name = 'your.model'
    
    @api.model
    def batch_process_with_commits(self, records):
        """Process records in batches with intermediate commits"""
        batch_size = 100
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            
            # Process batch
            for record in batch:
                record.process()
            
            # Commit after each batch to avoid long transactions
            self.env.cr.commit()
```

#### 3. Using threading for background tasks

```python
from odoo import models, api
import threading

class YourModel(models.Model):
    _name = 'your.model'
    
    @api.model
    def async_operation(self):
        """Start a background operation"""
        def background_task():
            with api.Environment.manage():
                new_cr = self.pool.cursor()
                try:
                    # Create new environment with new cursor
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    
                    # Your long operation here
                    # Use new_env instead of self.env
                    
                    new_cr.commit()
                except Exception as e:
                    new_cr.rollback()
                    _logger.error(f"Background task failed: {e}")
                finally:
                    new_cr.close()
        
        thread = threading.Thread(target=background_task)
        thread.start()
        
        return {'type': 'ir.actions.act_window_close'}
```

## Best Practices

### 1. Optimize Database Queries
- Add proper indexes to frequently queried fields
- Use `_auto_init()` to define indexes in models
- Avoid loading unnecessary fields with `fields` parameter
- Use `limit` in search operations when possible

```python
# Good
records = self.env['res.partner'].search([('active', '=', True)], 
                                         fields=['name', 'email'], 
                                         limit=100)

# Bad - loads all fields for all records
records = self.env['res.partner'].search([('active', '=', True)])
```

### 2. Use Batch Processing
```python
@api.model
def process_large_dataset(self, record_ids):
    batch_size = 100
    for i in range(0, len(record_ids), batch_size):
        batch_ids = record_ids[i:i+batch_size]
        records = self.browse(batch_ids)
        records.process()
        self.env.cr.commit()  # Commit each batch
```

### 3. Leverage Queue Jobs (Odoo Queue Module)
Install `queue_job` module for better handling of long-running tasks:

```python
from odoo.addons.queue_job.job import job

class YourModel(models.Model):
    _name = 'your.model'
    
    @job
    def long_running_task(self):
        # This will run in background
        pass
    
    def trigger_task(self):
        self.with_delay().long_running_task()
```

### 4. Monitor and Log
```python
import time
import logging

_logger = logging.getLogger(__name__)

class YourModel(models.Model):
    _name = 'your.model'
    
    @api.model
    def monitored_operation(self):
        start_time = time.time()
        try:
            # Your operation
            pass
        finally:
            elapsed = time.time() - start_time
            _logger.info(f"Operation completed in {elapsed:.2f} seconds")
            
            if elapsed > 60:
                _logger.warning(f"Operation took longer than expected: {elapsed:.2f}s")
```

## Debugging Timeout Issues

### 1. Enable Query Logging
In `odoo.conf`:
```ini
log_level = debug
log_db = True
log_db_level = warning
```

### 2. Use Odoo's Profiling
```python
from odoo.tools import profile

class YourModel(models.Model):
    _name = 'your.model'
    
    @profile('/tmp/profiling_output.txt')
    def method_to_profile(self):
        # Your code here
        pass
```

### 3. Check PostgreSQL Slow Queries
```sql
-- Enable slow query logging in PostgreSQL
ALTER DATABASE your_db SET log_min_duration_statement = 1000; -- Log queries > 1s

-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

### 4. Monitor Active Queries
```sql
-- Check currently running queries
SELECT pid, now() - query_start as duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

## Emergency Fixes

### Kill Stuck Queries
```sql
-- Find the process ID
SELECT pid, query FROM pg_stat_activity WHERE state = 'active';

-- Terminate gracefully
SELECT pg_cancel_backend(pid);

-- Force kill if needed
SELECT pg_terminate_backend(pid);
```

### Restart Odoo Workers
```bash
# For systemd
sudo systemctl restart odoo

# For manual restart
pkill -9 -f openerp-server
./odoo-bin -c /etc/odoo.conf
```

## Monitoring & Prevention

### 1. Setup Monitoring
- Use tools like Prometheus + Grafana
- Monitor response times, worker health, database connections
- Set up alerts for timeout occurrences

### 2. Regular Maintenance
- Vacuum PostgreSQL database regularly
- Update statistics: `ANALYZE;`
- Rebuild indexes periodically
- Archive old data

### 3. Load Testing
- Use tools like Locust or Apache JMeter
- Test with realistic concurrent users
- Identify bottlenecks before production issues

## Conclusion

Timeout issues in Odoo 17 are typically addressed through a combination of:
1. Proper configuration (Odoo, web server, database)
2. Code optimization (efficient queries, batch processing)
3. Infrastructure scaling (workers, resources)
4. Monitoring and proactive maintenance

Always test changes in a staging environment before applying to production.
