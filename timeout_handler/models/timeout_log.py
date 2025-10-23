# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class TimeoutLog(models.Model):
    """Log timeout occurrences for monitoring and analysis"""
    _name = 'timeout.log'
    _description = 'Timeout Log'
    _order = 'create_date desc'
    
    name = fields.Char(string='Operation Name', required=True, index=True)
    model_name = fields.Char(string='Model', index=True)
    method_name = fields.Char(string='Method', index=True)
    duration = fields.Float(string='Duration (seconds)', required=True)
    threshold = fields.Float(string='Threshold (seconds)')
    exceeded = fields.Boolean(
        string='Threshold Exceeded',
        compute='_compute_exceeded',
        store=True
    )
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    record_id = fields.Integer(string='Record ID')
    context_info = fields.Text(string='Context Information')
    error_message = fields.Text(string='Error Message')
    traceback = fields.Text(string='Traceback')
    create_date = fields.Datetime(string='Date', readonly=True, index=True)
    
    @api.depends('duration', 'threshold')
    def _compute_exceeded(self):
        for record in self:
            record.exceeded = record.threshold and record.duration > record.threshold
    
    @api.model
    def log_timeout(self, operation_name, duration, threshold=None, **kwargs):
        """
        Create a timeout log entry
        
        Args:
            operation_name: Name of the operation
            duration: Execution time in seconds
            threshold: Optional threshold value
            **kwargs: Additional fields (model_name, method_name, etc.)
        """
        values = {
            'name': operation_name,
            'duration': duration,
            'threshold': threshold,
        }
        values.update(kwargs)
        
        try:
            return self.create(values)
        except Exception as e:
            _logger.error(f"Failed to create timeout log: {str(e)}")
            return False
    
    @api.model
    def get_timeout_statistics(self, days=7):
        """
        Get timeout statistics for the last N days
        
        Returns:
            Dictionary with statistics
        """
        domain = [('create_date', '>=', fields.Datetime.now() - fields.timedelta(days=days))]
        logs = self.search(domain)
        
        if not logs:
            return {
                'total_count': 0,
                'exceeded_count': 0,
                'avg_duration': 0,
                'max_duration': 0,
            }
        
        return {
            'total_count': len(logs),
            'exceeded_count': len(logs.filtered('exceeded')),
            'avg_duration': sum(logs.mapped('duration')) / len(logs),
            'max_duration': max(logs.mapped('duration')),
            'by_model': self._group_by_model(logs),
        }
    
    def _group_by_model(self, logs):
        """Group logs by model"""
        result = {}
        for log in logs:
            if log.model_name:
                if log.model_name not in result:
                    result[log.model_name] = {
                        'count': 0,
                        'avg_duration': 0,
                        'total_duration': 0,
                    }
                result[log.model_name]['count'] += 1
                result[log.model_name]['total_duration'] += log.duration
                result[log.model_name]['avg_duration'] = (
                    result[log.model_name]['total_duration'] / 
                    result[log.model_name]['count']
                )
        return result
    
    @api.model
    def cleanup_old_logs(self, days=30):
        """
        Delete logs older than N days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted records
        """
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        old_logs = self.search([('create_date', '<', cutoff_date)])
        count = len(old_logs)
        old_logs.unlink()
        _logger.info(f"Cleaned up {count} timeout logs older than {days} days")
        return count


class TimeoutMonitorMixin(models.AbstractModel):
    """
    Mixin to add timeout monitoring to any model
    
    Usage:
        class MyModel(models.Model):
            _name = 'my.model'
            _inherit = ['my.model', 'timeout.monitor.mixin']
            
            @timeout_monitored(threshold=60)
            def my_slow_method(self):
                # Your code here
                pass
    """
    _name = 'timeout.monitor.mixin'
    _description = 'Timeout Monitoring Mixin'
    
    def timeout_monitored(self, threshold=300):
        """
        Decorator to monitor method execution time
        
        Args:
            threshold: Time threshold in seconds
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                import time
                start_time = time.time()
                
                try:
                    result = func(self, *args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Log if exceeded threshold
                    if duration > threshold:
                        self.env['timeout.log'].log_timeout(
                            operation_name=f"{self._name}.{func.__name__}",
                            model_name=self._name,
                            method_name=func.__name__,
                            duration=duration,
                            threshold=threshold,
                            record_id=self.id if len(self) == 1 else None,
                        )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # Log error
                    self.env['timeout.log'].log_timeout(
                        operation_name=f"{self._name}.{func.__name__}",
                        model_name=self._name,
                        method_name=func.__name__,
                        duration=duration,
                        threshold=threshold,
                        record_id=self.id if len(self) == 1 else None,
                        error_message=str(e),
                    )
                    raise
            
            return wrapper
        return decorator
