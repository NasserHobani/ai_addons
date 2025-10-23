# -*- coding: utf-8 -*-

import time
import logging
import functools
import threading
from contextlib import contextmanager
from datetime import datetime

from odoo import api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    """Exception raised when an operation times out"""
    pass


@contextmanager
def timeout_context(seconds, operation_name="Operation"):
    """
    Context manager for timeout handling with detailed logging
    
    Usage:
        with timeout_context(300, "Export Data"):
            # Your long operation here
            pass
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        _logger.info(f"{operation_name} completed in {elapsed:.2f} seconds")
        
        if elapsed > seconds:
            _logger.warning(
                f"{operation_name} exceeded timeout threshold: "
                f"{elapsed:.2f}s > {seconds}s"
            )


def with_timeout(seconds=300, raise_on_timeout=True):
    """
    Decorator to monitor execution time and optionally raise timeout
    
    Args:
        seconds: Maximum allowed execution time
        raise_on_timeout: Whether to raise exception on timeout
        
    Usage:
        @with_timeout(300)
        def long_running_method(self):
            # Your code here
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                if elapsed > seconds:
                    msg = f"{func.__name__} took {elapsed:.2f}s (threshold: {seconds}s)"
                    _logger.warning(msg)
                    
                    if raise_on_timeout:
                        raise TimeoutException(msg)
                
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(
                    f"{func.__name__} failed after {elapsed:.2f}s: {str(e)}"
                )
                raise
                
        return wrapper
    return decorator


def batch_process(records, batch_size=100, commit=True, progress_callback=None):
    """
    Process records in batches with optional auto-commit
    
    Args:
        records: Recordset to process
        batch_size: Number of records per batch
        commit: Whether to commit after each batch
        progress_callback: Optional function(processed, total) for progress
        
    Returns:
        Generator yielding batches of records
        
    Usage:
        for batch in batch_process(large_recordset, batch_size=50):
            for record in batch:
                record.process()
    """
    total = len(records)
    processed = 0
    
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        
        yield batch
        
        processed += len(batch)
        
        if commit and hasattr(records, 'env'):
            records.env.cr.commit()
            _logger.info(f"Committed batch {i//batch_size + 1}, processed {processed}/{total}")
        
        if progress_callback:
            progress_callback(processed, total)


class BatchProcessor:
    """
    Advanced batch processor with automatic commit and error handling
    
    Usage:
        processor = BatchProcessor(env, batch_size=100)
        for batch in processor.process(records):
            for record in batch:
                record.process_something()
    """
    
    def __init__(self, env, batch_size=100, commit_per_batch=True):
        self.env = env
        self.batch_size = batch_size
        self.commit_per_batch = commit_per_batch
        self.processed = 0
        self.failed = 0
        self.start_time = None
        
    def process(self, records, error_handler=None):
        """
        Process records in batches
        
        Args:
            records: Recordset to process
            error_handler: Optional function(record, error) for handling errors
            
        Yields:
            Batches of records
        """
        self.start_time = time.time()
        total = len(records)
        
        _logger.info(f"Starting batch processing of {total} records")
        
        for i in range(0, total, self.batch_size):
            batch = records[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            
            try:
                yield batch
                
                self.processed += len(batch)
                
                if self.commit_per_batch:
                    self.env.cr.commit()
                    _logger.info(
                        f"Batch {batch_num}: Committed {len(batch)} records "
                        f"({self.processed}/{total})"
                    )
                    
            except Exception as e:
                self.failed += len(batch)
                _logger.error(f"Batch {batch_num} failed: {str(e)}")
                
                if error_handler:
                    for record in batch:
                        try:
                            error_handler(record, e)
                        except:
                            pass
                else:
                    # Rollback and continue
                    self.env.cr.rollback()
        
        self._log_summary(total)
        
    def _log_summary(self, total):
        """Log processing summary"""
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0
        
        _logger.info(
            f"Batch processing completed: {self.processed}/{total} successful, "
            f"{self.failed} failed in {elapsed:.2f}s ({rate:.2f} records/sec)"
        )


def async_operation(env, uid, context, func, *args, **kwargs):
    """
    Execute operation asynchronously in a new thread with new cursor
    
    Args:
        env: Odoo environment
        uid: User ID
        context: Context dictionary
        func: Function to execute
        *args, **kwargs: Arguments for the function
        
    Returns:
        Thread object
        
    Usage:
        def my_long_task(env):
            # Do something with env
            pass
            
        thread = async_operation(self.env, self.env.uid, self.env.context, my_long_task)
        thread.start()
    """
    def thread_function():
        with api.Environment.manage():
            new_cr = env.registry.cursor()
            try:
                new_env = api.Environment(new_cr, uid, context)
                func(new_env, *args, **kwargs)
                new_cr.commit()
                _logger.info(f"Async operation {func.__name__} completed successfully")
            except Exception as e:
                new_cr.rollback()
                _logger.error(f"Async operation {func.__name__} failed: {str(e)}")
            finally:
                new_cr.close()
    
    thread = threading.Thread(target=thread_function)
    return thread


class ProgressTracker:
    """
    Track and log progress of long-running operations
    
    Usage:
        tracker = ProgressTracker(total_items=1000, log_interval=10)
        for item in items:
            process(item)
            tracker.increment()
    """
    
    def __init__(self, total_items, log_interval=10, operation_name="Processing"):
        self.total_items = total_items
        self.log_interval = log_interval
        self.operation_name = operation_name
        self.processed = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.last_log_count = 0
        
    def increment(self, count=1):
        """Increment processed count and log if needed"""
        self.processed += count
        
        # Calculate progress percentage
        progress_pct = (self.processed / self.total_items * 100) if self.total_items > 0 else 0
        
        # Check if we should log
        current_time = time.time()
        time_since_log = current_time - self.last_log_time
        
        if time_since_log >= self.log_interval or self.processed == self.total_items:
            self._log_progress(progress_pct, time_since_log)
            self.last_log_time = current_time
            self.last_log_count = self.processed
            
    def _log_progress(self, progress_pct, time_interval):
        """Log current progress"""
        elapsed_total = time.time() - self.start_time
        records_per_sec = self.processed / elapsed_total if elapsed_total > 0 else 0
        
        # Estimate time remaining
        if records_per_sec > 0:
            remaining_records = self.total_items - self.processed
            eta_seconds = remaining_records / records_per_sec
            eta_str = f", ETA: {eta_seconds:.0f}s"
        else:
            eta_str = ""
        
        _logger.info(
            f"{self.operation_name}: {self.processed}/{self.total_items} "
            f"({progress_pct:.1f}%) - {records_per_sec:.2f} items/sec{eta_str}"
        )
        
    def finish(self):
        """Log final summary"""
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0
        
        _logger.info(
            f"{self.operation_name} completed: {self.processed} items in "
            f"{elapsed:.2f}s ({rate:.2f} items/sec)"
        )


@contextmanager
def query_monitor(threshold_seconds=1.0, log_query=False):
    """
    Monitor database query execution time
    
    Args:
        threshold_seconds: Log warning if query exceeds this time
        log_query: Whether to log the actual SQL query
        
    Usage:
        with query_monitor(threshold_seconds=2.0):
            env['res.partner'].search([])
    """
    start_time = time.time()
    
    yield
    
    elapsed = time.time() - start_time
    
    if elapsed > threshold_seconds:
        _logger.warning(
            f"Slow query detected: {elapsed:.3f}s "
            f"(threshold: {threshold_seconds}s)"
        )


def retry_on_timeout(max_attempts=3, delay=1, backoff=2):
    """
    Decorator to retry operation on timeout with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        
    Usage:
        @retry_on_timeout(max_attempts=3, delay=2)
        def flaky_operation(self):
            # Operation that might timeout
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except TimeoutException as e:
                    if attempt == max_attempts:
                        _logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
                        raise
                    
                    _logger.warning(
                        f"{func.__name__} timed out (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
                    
        return wrapper
    return decorator


def safe_commit(cr, operation_name="Operation"):
    """
    Safely commit database cursor with error handling
    
    Args:
        cr: Database cursor
        operation_name: Name for logging
    """
    try:
        cr.commit()
        _logger.debug(f"{operation_name}: commit successful")
    except Exception as e:
        _logger.error(f"{operation_name}: commit failed - {str(e)}")
        try:
            cr.rollback()
        except:
            pass
        raise


def chunked_ids(ids, chunk_size=100):
    """
    Split list of IDs into chunks
    
    Usage:
        for id_chunk in chunked_ids(record_ids, chunk_size=50):
            records = env['model.name'].browse(id_chunk)
            records.process()
    """
    for i in range(0, len(ids), chunk_size):
        yield ids[i:i+chunk_size]
