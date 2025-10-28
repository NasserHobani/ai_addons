# Quick Start Guide: Fixing Odoo 17 Timeouts

## 🚀 5-Minute Fix

If you're experiencing timeout errors right now, follow these steps:

### Step 1: Update Odoo Configuration (2 minutes)

Edit `/etc/odoo/odoo.conf`:

```ini
[options]
# Increase these timeout values
limit_time_cpu = 600          # Was: 60
limit_time_real = 1200        # Was: 120
limit_time_real_cron = 3600   # Was: -1 or 300

# Increase worker limits if needed
workers = 4                    # Adjust based on CPU cores
limit_memory_soft = 2147483648 # 2GB
db_maxconn = 64
```

Restart Odoo:
```bash
sudo systemctl restart odoo
```

### Step 2: Update Nginx Configuration (2 minutes)

Edit your Nginx config (usually `/etc/nginx/sites-available/odoo`):

```nginx
server {
    # ... existing config ...
    
    # Add these timeout settings
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    send_timeout 600s;
    client_body_timeout 600s;
}
```

Test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Verify (1 minute)

1. Try the operation that was timing out
2. Check logs: `sudo tail -f /var/log/odoo/odoo-server.log`
3. Monitor for 504 errors: `sudo tail -f /var/log/nginx/odoo-error.log`

## ✅ That's It!

This should resolve 80% of timeout issues. If problems persist, continue below.

---

## 🔧 For Persistent Issues

### Check Database Performance

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check active queries
SELECT pid, now() - query_start as duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

### Apache Users

If you use Apache instead of Nginx, add to your config:

```apache
<VirtualHost *:443>
    # Add these lines
    Timeout 600
    ProxyTimeout 600
    
    <Location />
        ProxyPass http://localhost:8069/ timeout=600
        ProxyPassReverse http://localhost:8069/
    </Location>
</VirtualHost>
```

Reload:
```bash
sudo systemctl reload apache2
```

### PostgreSQL Configuration

Edit `/etc/postgresql/*/main/postgresql.conf`:

```ini
statement_timeout = 300000  # 5 minutes in milliseconds
max_connections = 200
shared_buffers = 256MB
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## 📊 Install Monitoring Module

For long-term monitoring and prevention:

```bash
# 1. Copy the timeout_handler module
cp -r timeout_handler /opt/odoo/custom_addons/

# 2. Restart Odoo
sudo systemctl restart odoo

# 3. Install via UI
# Apps → Update Apps List → Search "Timeout Handler" → Install
```

### Use in Your Code

```python
from odoo.addons.timeout_handler.utils import with_timeout, batch_process

class MyModel(models.Model):
    _name = 'my.model'
    
    @with_timeout(300)
    def my_method(self):
        # Your code here
        pass
    
    def process_many_records(self):
        records = self.env['res.partner'].search([])
        for batch in batch_process(records, batch_size=100):
            for record in batch:
                record.process()
```

---

## 🎯 Common Scenarios

### Scenario 1: Report Generation Timeouts

**Quick Fix:**
```python
# Use batch processing
from odoo.addons.timeout_handler.utils import batch_process

def generate_report(self):
    records = self.get_report_records()
    for batch in batch_process(records, batch_size=50):
        self.process_batch(batch)
```

### Scenario 2: CSV Import Timeouts

**Quick Fix:**
- Increase: `limit_time_real = 1800` (30 minutes)
- Or use background job: `self.with_delay().import_csv(file_data)`

### Scenario 3: Cron Jobs Timing Out

**Quick Fix:**
```ini
# In odoo.conf
limit_time_real_cron = 3600  # 1 hour for cron jobs
max_cron_threads = 2
```

### Scenario 4: API Calls Timing Out

**Quick Fix:**
```python
# Use retry mechanism
from odoo.addons.timeout_handler.utils import retry_on_timeout

@retry_on_timeout(max_attempts=3, delay=2)
def call_external_api(self):
    return requests.get(url, timeout=30)
```

---

## 📱 Monitoring Commands

### Watch for Timeouts
```bash
# Monitor Odoo logs
sudo tail -f /var/log/odoo/odoo-server.log | grep -i timeout

# Monitor Nginx 504 errors
sudo tail -f /var/log/nginx/odoo-error.log | grep 504

# Monitor PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### Check System Health
```bash
# Worker processes
ps aux | grep odoo | wc -l

# Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='your_database';"

# Memory usage
free -h

# CPU usage
htop
```

---

## 🆘 Emergency: Kill Stuck Processes

### Kill Stuck Odoo Worker
```bash
# Find process
ps aux | grep odoo

# Kill specific worker
sudo kill -9 <PID>

# Or restart all
sudo systemctl restart odoo
```

### Kill Stuck Database Query
```sql
-- Find stuck queries
SELECT pid, query FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';

-- Kill gracefully
SELECT pg_cancel_backend(<pid>);

-- Force kill if needed
SELECT pg_terminate_backend(<pid>);
```

---

## 📚 Full Documentation

For comprehensive information:

- **[ODOO_17_TIMEOUTS.md](./ODOO_17_TIMEOUTS.md)** - Complete guide with all solutions
- **[timeout_handler/README.md](./timeout_handler/README.md)** - Module documentation
- **[odoo.conf.example](./odoo.conf.example)** - Full configuration example
- **[nginx.conf.example](./nginx.conf.example)** - Nginx configuration
- **[apache.conf.example](./apache.conf.example)** - Apache configuration

---

## ✨ Prevention Tips

1. **Add Database Indexes**: For frequently queried fields
   ```python
   _sql_constraints = [
       ('my_field_index', 'CREATE INDEX IF NOT EXISTS my_field_idx ON table_name(field_name)', 'Index creation')
   ]
   ```

2. **Use Batch Processing**: Always process large datasets in chunks

3. **Archive Old Data**: Reduce database size regularly

4. **Monitor Regularly**: Check timeout logs weekly

5. **Update Configuration**: After major data growth

---

## Need Help?

1. Check logs: `/var/log/odoo/odoo-server.log`
2. Review documentation: `ODOO_17_TIMEOUTS.md`
3. Enable debug mode: `log_level = debug` in odoo.conf
4. Profile slow methods: Use `@profile` decorator

---

**Last Updated**: 2025-10-23  
**Tested with**: Odoo 17.0  
**Status**: Production Ready ✅
