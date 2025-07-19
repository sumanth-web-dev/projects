"""
Monitoring service for system health and performance metrics.

This module provides functionality for tracking system health, performance metrics,
and resource usage throughout the application.
"""
import os
import time
import logging
import threading
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from flask import Flask
from sqlalchemy import text
from models.database import db
import threading 


# Set up logging
logger = logging.getLogger(__name__)


class SystemMetrics:
    """Model for storing system metrics data."""
    
    def __init__(self, timestamp: datetime, cpu_usage: float, memory_usage: float,
                disk_usage: float, active_connections: int, 
                db_connection_pool: Dict[str, Any]):
        """Initialize system metrics.
        
        Args:
            timestamp: Time when metrics were collected
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
            active_connections: Number of active connections
            db_connection_pool: Database connection pool stats
        """
        self.timestamp = timestamp
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.disk_usage = disk_usage
        self.active_connections = active_connections
        self.db_connection_pool = db_connection_pool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'active_connections': self.active_connections,
            'db_connection_pool': self.db_connection_pool
        }


class ApplicationMetrics:
    """Model for storing application-specific metrics."""
    
    def __init__(self, timestamp: datetime, request_count: int, error_count: int,
                avg_response_time: float, active_users: int):
        """Initialize application metrics.
        
        Args:
            timestamp: Time when metrics were collected
            request_count: Number of requests processed
            error_count: Number of errors encountered
            avg_response_time: Average response time in milliseconds
            active_users: Number of active users
        """
        self.timestamp = timestamp
        self.request_count = request_count
        self.error_count = error_count
        self.avg_response_time = avg_response_time
        self.active_users = active_users
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'request_count': self.request_count,
            'error_count': self.error_count,
            'avg_response_time': self.avg_response_time,
            'active_users': self.active_users
        }


class AutomationMetrics:
    """Model for storing automation-specific metrics."""
    
    def __init__(self, timestamp: datetime, active_sessions: int, 
                jobs_processed: int, applications_submitted: int,
                success_rate: float, avg_application_time: float):
        """Initialize automation metrics.
        
        Args:
            timestamp: Time when metrics were collected
            active_sessions: Number of active automation sessions
            jobs_processed: Number of jobs processed
            applications_submitted: Number of applications submitted
            success_rate: Success rate percentage
            avg_application_time: Average time to complete an application in seconds
        """
        self.timestamp = timestamp
        self.active_sessions = active_sessions
        self.jobs_processed = jobs_processed
        self.applications_submitted = applications_submitted
        self.success_rate = success_rate
        self.avg_application_time = avg_application_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'active_sessions': self.active_sessions,
            'jobs_processed': self.jobs_processed,
            'applications_submitted': self.applications_submitted,
            'success_rate': self.success_rate,
            'avg_application_time': self.avg_application_time
        }


class MonitoringService:
    """Service for monitoring system health and performance."""
    
    def __init__(self, app=None):
        """Initialize the monitoring service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.monitoring_enabled = True
        self.metrics_interval = 60  # seconds
        self.metrics_retention = 7  # days
        self.alert_thresholds = {
            'cpu_usage': 80.0,  # percentage
            'memory_usage': 80.0,  # percentage
            'disk_usage': 80.0,  # percentage
            'error_rate': 5.0,  # percentage
            'response_time': 1000.0  # milliseconds
        }
        self.system_metrics = []
        self.application_metrics = []
        self.automation_metrics = []
        self._collection_thread = None
        self._stop_collection = threading.Event()
        self._alert_callbacks = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the monitoring service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Load configuration
        self.monitoring_enabled = app.config.get('MONITORING_ENABLED', True)
        self.metrics_interval = app.config.get('METRICS_INTERVAL', 60)
        self.metrics_retention = app.config.get('METRICS_RETENTION_DAYS', 7)
        
        # Load alert thresholds
        thresholds = app.config.get('ALERT_THRESHOLDS', {})
        for key, value in thresholds.items():
            if key in self.alert_thresholds:
                self.alert_thresholds[key] = value
        
        # Create metrics table if it doesn't exist
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'system_metrics' not in inspector.get_table_names():
                self._create_metrics_tables()
        
        # Start metrics collection if enabled
        if self.monitoring_enabled:
            self.start_metrics_collection()
            
            # Register cleanup on app shutdown
            app.teardown_appcontext(self._cleanup)
    
    def _create_metrics_tables(self):
        """Create metrics tables if they don't exist."""
        try:
            # Use SQLAlchemy 2.0 syntax with text()
            from sqlalchemy import text
            
            # System metrics table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    disk_usage REAL NOT NULL,
                    active_connections INTEGER NOT NULL,
                    db_connection_pool TEXT NOT NULL
                )
            """))
            
            # Application metrics table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS application_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    request_count INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    avg_response_time REAL NOT NULL,
                    active_users INTEGER NOT NULL
                )
            """))
            
            # Automation metrics table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS automation_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    active_sessions INTEGER NOT NULL,
                    jobs_processed INTEGER NOT NULL,
                    applications_submitted INTEGER NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_application_time REAL NOT NULL
                )
            """))
            
            # Create index on timestamp for faster queries
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics (timestamp)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_application_metrics_timestamp ON application_metrics (timestamp)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_automation_metrics_timestamp ON automation_metrics (timestamp)"))
            
            # Commit the changes
            db.session.commit()
            
            logger.info("Metrics tables created successfully")
        except Exception as e:
            logger.error(f"Error creating metrics tables: {str(e)}")
    
    def start_metrics_collection(self):
        """Start collecting metrics in a background thread."""
        if self._collection_thread is not None and self._collection_thread.is_alive():
            logger.warning("Metrics collection already running")
            return
        
        self._stop_collection.clear()
        self._collection_thread = threading.Thread(
            target=self._collect_metrics_loop,
            daemon=True
        )
        self._collection_thread.start()
        logger.info(f"Started metrics collection (interval: {self.metrics_interval}s)")
    
   

    def stop_metrics_collection(self):
        """Stop collecting metrics."""
        if self._collection_thread is None or not self._collection_thread.is_alive():
            logger.warning("Metrics collection not running")
            return

        self._stop_collection.set()

        # Avoid joining the current thread
        if threading.current_thread() != self._collection_thread:
            self._collection_thread.join(timeout=5.0)
            logger.info("Stopped metrics collection")
        else:
            logger.warning("Called stop_metrics_collection from within the collection thread; skipping join()")

        self._collection_thread = None

        logger.info("Stopped metrics collection")
    
    def _cleanup(self, exception=None):
        """Clean up resources when the app context ends."""
        self.stop_metrics_collection()
    
    def _collect_metrics_loop(self):
        """Continuously collect metrics at the specified interval."""
        while not self._stop_collection.is_set():
            try:
                # Collect metrics
                self.collect_system_metrics()
                
                # Check for alerts
                self._check_alerts()
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {str(e)}")
            
            # Wait for the next collection interval or until stopped
            self._stop_collection.wait(self.metrics_interval)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system metrics.
        
        Returns:
            SystemMetrics: Collected metrics
        """
        try:
            # Get current timestamp
            timestamp = datetime.utcnow()
            
            # Collect CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Collect memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Collect disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Collect network connections
            connections = len(psutil.net_connections())
            
            # Collect database connection pool stats
            db_stats = {}
            if self.app is not None:
                with self.app.app_context():
                    try:
                        # Get SQLAlchemy connection pool stats
                        engine = db.get_engine()
                        pool = engine.pool
                        db_stats = {
                            'size': pool.size(),
                            'checkedin': pool.checkedin(),
                            'overflow': pool.overflow(),
                            'checkedout': pool.checkedout()
                        }
                    except Exception as e:
                        logger.error(f"Error getting database stats: {str(e)}")
                        db_stats = {'error': str(e)}
            
            # Create metrics object
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                active_connections=connections,
                db_connection_pool=db_stats
            )
            
            # Store metrics
            self.system_metrics.append(metrics)
            
            # Limit in-memory metrics to most recent
            if len(self.system_metrics) > 1000:
                self.system_metrics = self.system_metrics[-1000:]
            
            # Store in database if app context is available
            if self.app is not None:
                with self.app.app_context():
                    try:
                        db.session.execute(text(
                            """
                            INSERT INTO system_metrics 
                            (timestamp, cpu_usage, memory_usage, disk_usage, active_connections, db_connection_pool)
                            VALUES (:timestamp, :cpu, :memory, :disk, :connections, :db_stats)
                            """
                        ), {
                            "timestamp": timestamp, 
                            "cpu": cpu_usage, 
                            "memory": memory_usage, 
                            "disk": disk_usage, 
                            "connections": connections, 
                            "db_stats": json.dumps(db_stats)
                        })
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error storing system metrics: {str(e)}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return None
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics.
        
        Returns:
            ApplicationMetrics: Collected metrics
        """
        try:
            # Get current timestamp
            timestamp = datetime.utcnow()
            
            # These metrics would typically be collected from the application
            # For now, we'll use placeholder values
            request_count = 0
            error_count = 0
            avg_response_time = 0.0
            active_users = 0
            
            # In a real implementation, we would collect these from the app
            if self.app is not None:
                with self.app.app_context():
                    # Example: Count active users from database
                    try:
                        result = db.session.execute(text(
                            "SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-15 minutes')"
                        ))
                        active_users = result.scalar() or 0
                    except Exception as e:
                        logger.error(f"Error counting active users: {str(e)}")
            
            # Create metrics object
            metrics = ApplicationMetrics(
                timestamp=timestamp,
                request_count=request_count,
                error_count=error_count,
                avg_response_time=avg_response_time,
                active_users=active_users
            )
            
            # Store metrics
            self.application_metrics.append(metrics)
            
            # Limit in-memory metrics to most recent
            if len(self.application_metrics) > 1000:
                self.application_metrics = self.application_metrics[-1000:]
            
            # Store in database if app context is available
            if self.app is not None:
                with self.app.app_context():
                    try:
                        db.session.execute(text(
                            """
                            INSERT INTO application_metrics 
                            (timestamp, request_count, error_count, avg_response_time, active_users)
                            VALUES (:timestamp, :req_count, :err_count, :avg_time, :active_users)
                            """
                        ), {
                            "timestamp": timestamp,
                            "req_count": request_count,
                            "err_count": error_count,
                            "avg_time": avg_response_time,
                            "active_users": active_users
                        })
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error storing application metrics: {str(e)}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {str(e)}")
            return None
    
    def collect_automation_metrics(self) -> AutomationMetrics:
        """Collect automation-specific metrics.
        
        Returns:
            AutomationMetrics: Collected metrics
        """
        try:
            # Get current timestamp
            timestamp = datetime.utcnow()
            
            # These metrics would typically be collected from the automation system
            # For now, we'll use placeholder values
            active_sessions = 0
            jobs_processed = 0
            applications_submitted = 0
            success_rate = 0.0
            avg_application_time = 0.0
            
            # In a real implementation, we would collect these from the database
            if self.app is not None:
                with self.app.app_context():
                    try:
                        # Count active automation sessions
                        result = db.session.execute(text(
                            "SELECT COUNT(*) FROM applications WHERE status = 'in_progress'"
                        ))
                        active_sessions = result.scalar() or 0
                        
                        # Count applications submitted in the last 24 hours
                        result = db.session.execute(text(
                            "SELECT COUNT(*) FROM applications WHERE submitted_at > datetime('now', '-1 day')"
                        ))
                        applications_submitted = result.scalar() or 0
                        
                        # Calculate success rate
                        result = db.session.execute(text(
                            """
                            SELECT 
                                COUNT(CASE WHEN status = 'submitted' THEN 1 END) * 100.0 / COUNT(*) as success_rate
                            FROM applications
                            WHERE created_at > datetime('now', '-1 day')
                            """
                        ))
                        success_rate = result.scalar() or 0.0
                        
                    except Exception as e:
                        logger.error(f"Error collecting automation metrics from database: {str(e)}")
            
            # Create metrics object
            metrics = AutomationMetrics(
                timestamp=timestamp,
                active_sessions=active_sessions,
                jobs_processed=jobs_processed,
                applications_submitted=applications_submitted,
                success_rate=success_rate,
                avg_application_time=avg_application_time
            )
            
            # Store metrics
            self.automation_metrics.append(metrics)
            
            # Limit in-memory metrics to most recent
            if len(self.automation_metrics) > 1000:
                self.automation_metrics = self.automation_metrics[-1000:]
            
            # Store in database if app context is available
            if self.app is not None:
                with self.app.app_context():
                    try:
                        db.session.execute(text(
                            """
                            INSERT INTO automation_metrics 
                            (timestamp, active_sessions, jobs_processed, applications_submitted, 
                             success_rate, avg_application_time)
                            VALUES (:timestamp, :active_sessions, :jobs_processed, :applications_submitted, 
                             :success_rate, :avg_application_time)
                            """
                        ), {
                            "timestamp": timestamp, 
                            "active_sessions": active_sessions, 
                            "jobs_processed": jobs_processed, 
                            "applications_submitted": applications_submitted,
                            "success_rate": success_rate, 
                            "avg_application_time": avg_application_time
                        })
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error storing automation metrics: {str(e)}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting automation metrics: {str(e)}")
            return None
    
    def _check_alerts(self):
        """Check metrics against alert thresholds and trigger alerts if needed."""
        try:
            # Get the most recent system metrics
            if not self.system_metrics:
                return
            
            metrics = self.system_metrics[-1]
            alerts = []
            
            # Check CPU usage
            if metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
                alerts.append({
                    'type': 'system',
                    'level': 'warning',
                    'message': f"High CPU usage: {metrics.cpu_usage:.1f}% (threshold: {self.alert_thresholds['cpu_usage']}%)"
                })
            
            # Check memory usage
            if metrics.memory_usage > self.alert_thresholds['memory_usage']:
                alerts.append({
                    'type': 'system',
                    'level': 'warning',
                    'message': f"High memory usage: {metrics.memory_usage:.1f}% (threshold: {self.alert_thresholds['memory_usage']}%)"
                })
            
            # Check disk usage
            if metrics.disk_usage > self.alert_thresholds['disk_usage']:
                alerts.append({
                    'type': 'system',
                    'level': 'warning',
                    'message': f"High disk usage: {metrics.disk_usage:.1f}% (threshold: {self.alert_thresholds['disk_usage']}%)"
                })
            
            # Trigger alerts
            for alert in alerts:
                self._trigger_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {str(e)}")
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger an alert.
        
        Args:
            alert: Alert information
        """
        # Log the alert
        log_level = logging.WARNING if alert['level'] == 'warning' else logging.ERROR
        logger.log(log_level, f"ALERT: {alert['message']}")
        
        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
        
        # Store alert in database if app context is available
        if self.app is not None:
            with self.app.app_context():
                try:
                    # Check if we have a system_alerts table, create if not
                    if not db.engine.has_table('system_alerts'):
                        db.engine.execute("""
                            CREATE TABLE IF NOT EXISTS system_alerts (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                alert_type TEXT NOT NULL,
                                level TEXT NOT NULL,
                                message TEXT NOT NULL,
                                acknowledged BOOLEAN DEFAULT FALSE
                            )
                        """)
                    
                    # Insert the alert
                    db.engine.execute(
                        """
                        INSERT INTO system_alerts (alert_type, level, message)
                        VALUES (?, ?, ?)
                        """,
                        alert['type'], alert['level'], alert['message']
                    )
                except Exception as e:
                    logger.error(f"Error storing alert: {str(e)}")
    
    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for alerts.
        
        Args:
            callback: Function to call when an alert is triggered
        """
        self._alert_callbacks.append(callback)
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics data."""
        if self.app is None:
            return

        try:
            with self.app.app_context():
                cutoff_date = datetime.utcnow() - timedelta(days=self.metrics_retention)

                # Get a connection from the engine
                with db.engine.connect() as connection:
                    connection.execute(
                        text("DELETE FROM system_metrics WHERE timestamp < :cutoff"),
                        {"cutoff": cutoff_date}
                    )
                    connection.execute(
                        text("DELETE FROM application_metrics WHERE timestamp < :cutoff"),
                        {"cutoff": cutoff_date}
                    )
                    connection.execute(
                        text("DELETE FROM automation_metrics WHERE timestamp < :cutoff"),
                        {"cutoff": cutoff_date}
                    )

                logger.debug(f"Cleaned up metrics older than {cutoff_date}")
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")

    
    def get_system_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get system metrics for the specified time period.
        
        Args:
            hours: Number of hours to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of system metrics
        """
        if self.app is None:
            # Return in-memory metrics if no app context
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return [m.to_dict() for m in self.system_metrics if m.timestamp >= cutoff]
        
        try:
            with self.app.app_context():
                cutoff_date = datetime.utcnow() - timedelta(hours=hours)
                
                result = db.engine.execute(
                    """
                    SELECT timestamp, cpu_usage, memory_usage, disk_usage, 
                           active_connections, db_connection_pool
                    FROM system_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    cutoff_date
                )
                
                metrics = []
                for row in result:
                    db_pool = json.loads(row[5]) if row[5] else {}
                    metrics.append({
                        'timestamp': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                        'cpu_usage': row[1],
                        'memory_usage': row[2],
                        'disk_usage': row[3],
                        'active_connections': row[4],
                        'db_connection_pool': db_pool
                    })
                
                return metrics
        except Exception as e:
            logger.error(f"Error retrieving system metrics: {str(e)}")
            return []
    
    def get_application_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get application metrics for the specified time period.
        
        Args:
            hours: Number of hours to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of application metrics
        """
        if self.app is None:
            # Return in-memory metrics if no app context
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return [m.to_dict() for m in self.application_metrics if m.timestamp >= cutoff]
        
        try:
            with self.app.app_context():
                cutoff_date = datetime.utcnow() - timedelta(hours=hours)
                
                result = db.engine.execute(
                    """
                    SELECT timestamp, request_count, error_count, avg_response_time, active_users
                    FROM application_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    cutoff_date
                )
                
                metrics = []
                for row in result:
                    metrics.append({
                        'timestamp': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                        'request_count': row[1],
                        'error_count': row[2],
                        'avg_response_time': row[3],
                        'active_users': row[4]
                    })
                
                return metrics
        except Exception as e:
            logger.error(f"Error retrieving application metrics: {str(e)}")
            return []
    
    def get_automation_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get automation metrics for the specified time period.
        
        Args:
            hours: Number of hours to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of automation metrics
        """
        if self.app is None:
            # Return in-memory metrics if no app context
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return [m.to_dict() for m in self.automation_metrics if m.timestamp >= cutoff]
        
        try:
            with self.app.app_context():
                cutoff_date = datetime.utcnow() - timedelta(hours=hours)
                
                result = db.engine.execute(
                    """
                    SELECT timestamp, active_sessions, jobs_processed, applications_submitted,
                           success_rate, avg_application_time
                    FROM automation_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    cutoff_date
                )
                
                metrics = []
                for row in result:
                    metrics.append({
                        'timestamp': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                        'active_sessions': row[1],
                        'jobs_processed': row[2],
                        'applications_submitted': row[3],
                        'success_rate': row[4],
                        'avg_application_time': row[5]
                    })
                
                return metrics
        except Exception as e:
            logger.error(f"Error retrieving automation metrics: {str(e)}")
            return []
    
    def get_system_alerts(self, acknowledged: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system alerts.
        
        Args:
            acknowledged: Whether to include acknowledged alerts
            limit: Maximum number of alerts to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of system alerts
        """
        if self.app is None:
            return []
        
        try:
            with self.app.app_context():
                query = """
                    SELECT id, timestamp, alert_type, level, message, acknowledged
                    FROM system_alerts
                """
                
                params = []
                
                if not acknowledged:
                    query += " WHERE acknowledged = FALSE"
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                result = db.engine.execute(query, *params)
                
                alerts = []
                for row in result:
                    alerts.append({
                        'id': row[0],
                        'timestamp': row[1].isoformat() if isinstance(row[1], datetime) else row[1],
                        'type': row[2],
                        'level': row[3],
                        'message': row[4],
                        'acknowledged': bool(row[5])
                    })
                
                return alerts
        except Exception as e:
            logger.error(f"Error retrieving system alerts: {str(e)}")
            return []
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge a system alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.app is None:
            return False
        
        try:
            with self.app.app_context():
                db.engine.execute(
                    "UPDATE system_alerts SET acknowledged = TRUE WHERE id = ?",
                    alert_id
                )
                
                return True
        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            return False


# Create a singleton instance
monitoring_service = MonitoringService()