# Odoo 17 Timeout Solutions

This repository contains comprehensive documentation and tools for handling timeout issues in Odoo 17.

## Contents

### 📚 Documentation

- **[ODOO_17_TIMEOUTS.md](./ODOO_17_TIMEOUTS.md)** - Complete guide covering:
  - Common timeout scenarios and causes
  - Configuration solutions for Odoo, PostgreSQL, Nginx, and Apache
  - Python code patterns and best practices
  - Debugging techniques
  - Monitoring and prevention strategies

### ⚙️ Configuration Files

- **[odoo.conf.example](./odoo.conf.example)** - Optimized Odoo configuration with:
  - Extended timeout limits (CPU, real-time, cron)
  - Worker and memory settings
  - Database connection pooling
  - Performance tuning parameters

- **[nginx.conf.example](./nginx.conf.example)** - Nginx reverse proxy configuration with:
  - Extended proxy timeouts (600s default)
  - Long-polling and websocket support
  - SSL/TLS configuration
  - Caching and compression settings
  - Load balancing examples

- **[apache.conf.example](./apache.conf.example)** - Apache configuration with:
  - Proxy timeout settings
  - Websocket support
  - Load balancing configuration
  - Security headers and rate limiting

### 🔧 Odoo Module: timeout_handler

A complete Odoo 17 module providing:

#### Features
- **Timeout Monitoring**: Decorators and context managers for tracking execution time
- **Batch Processing**: Process large datasets with automatic commits
- **Async Operations**: Background task execution with proper cursor management
- **Progress Tracking**: Built-in logging and progress reporting
- **Timeout Logging**: Database tracking of timeout occurrences
- **Retry Mechanisms**: Automatic retry with exponential backoff

#### Quick Start

```python
from odoo import models, api
from odoo.addons.timeout_handler.utils import with_timeout, batch_process

class MyModel(models.Model):
    _name = 'my.model'
    
    @with_timeout(300)  # 5 minutes timeout
    @api.model
    def long_operation(self):
        # Your code here
        pass
    
    def process_large_dataset(self):
        records = self.env['res.partner'].search([])
        for batch in batch_process(records, batch_size=100):
            for record in batch:
                record.process_something()
            # Auto-commits after each batch
```

See [timeout_handler/README.md](./timeout_handler/README.md) for complete usage documentation.

## Common Timeout Issues & Quick Fixes

### 🔴 HTTP 504 Gateway Timeout

**Quick Fix:**
1. Update Nginx/Apache timeout settings (see config examples)
2. Increase `limit_time_real` in odoo.conf to 1200s
3. Check for slow database queries

### 🔴 Worker Killed During Operations

**Quick Fix:**
1. Increase `limit_time_cpu` and `limit_time_real` in odoo.conf
2. Use batch processing for large operations
3. Consider background jobs for very long tasks

### 🔴 Database Connection Timeout

**Quick Fix:**
1. Increase `db_maxconn` in odoo.conf
2. Optimize queries with proper indexes
3. Check PostgreSQL `max_connections` setting

## Installation

### 1. Apply Configuration Changes

```bash
# Backup current configuration
sudo cp /etc/odoo/odoo.conf /etc/odoo/odoo.conf.backup

# Update odoo.conf with recommended settings
sudo nano /etc/odoo/odoo.conf

# Restart Odoo
sudo systemctl restart odoo
```

### 2. Update Web Server Configuration

For Nginx:
```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/odoo
sudo ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

For Apache:
```bash
sudo cp apache.conf.example /etc/apache2/sites-available/odoo.conf
sudo a2ensite odoo.conf
sudo a2enmod proxy proxy_http headers rewrite ssl
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### 3. Install timeout_handler Module

```bash
# Copy module to addons directory
cp -r timeout_handler /opt/odoo/custom_addons/

# Update Odoo
./odoo-bin -u timeout_handler -d your_database

# Or install via UI: Apps → Search "Timeout Handler" → Install
```

## Monitoring

After implementation, monitor your system:

```bash
# Watch Odoo logs
sudo tail -f /var/log/odoo/odoo-server.log

# Monitor Nginx errors
sudo tail -f /var/log/nginx/odoo-error.log | grep 504

# Check PostgreSQL slow queries
sudo -u postgres psql -d your_database -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

## Best Practices

1. **Start with Configuration**: Apply recommended timeout settings before code changes
2. **Monitor First**: Use timeout_handler module to identify actual bottlenecks
3. **Optimize Queries**: Add database indexes for frequently queried fields
4. **Use Batch Processing**: Process large datasets in chunks with commits
5. **Background Jobs**: Use queue_job module for truly long-running tasks
6. **Regular Maintenance**: Vacuum PostgreSQL, archive old data, review logs

## Troubleshooting

### Still Getting Timeouts?

1. Check all timeout layers:
   - Web server (Nginx/Apache)
   - Odoo configuration
   - PostgreSQL
   - Load balancer (if applicable)

2. Enable detailed logging:
   ```ini
   [options]
   log_level = debug
   log_db = True
   ```

3. Profile slow operations:
   ```python
   from odoo.tools import profile
   
   @profile('/tmp/profile.txt')
   def slow_method(self):
       pass
   ```

4. Check system resources:
   ```bash
   # CPU and memory
   htop
   
   # Database connections
   sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Odoo workers
   ps aux | grep odoo
   ```

## Contributing

This repository was created to investigate and solve Odoo 17 timeout issues. Contributions are welcome!

## License

LGPL-3

## Support

For detailed information on specific topics, refer to:
- [Complete Timeout Guide](./ODOO_17_TIMEOUTS.md)
- [Module Documentation](./timeout_handler/README.md)
- Configuration examples in this repository