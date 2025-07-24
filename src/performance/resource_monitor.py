"""
Resource Monitoring & Performance Profiling
==========================================

Real - time system resource monitoring and performance profiling
for systematic review automation.

This module provides:
- CPU, memory, disk I / O monitoring
- Performance profiling and bottleneck detection
- Resource utilization alerts
- Performance reporting and analytics

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import functools
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics snapshot"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    process_count: int = 0
    load_average: float = 0.0


@dataclass
class PerformanceProfile:
    """Performance profile for a function / operation"""

    function_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    average_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    last_call: Optional[datetime] = None

    def update(self, execution_time_ms: float, memory_mb: float = 0.0):
        """Update profile with new measurement"""
        self.call_count += 1
        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.average_time_ms = self.total_time_ms / self.call_count
        self.memory_usage_mb = max(self.memory_usage_mb, memory_mb)
        self.last_call = datetime.now(timezone.utc)


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""

    report_id: str
    generated_at: datetime
    duration_seconds: float
    system_metrics_summary: Dict[str, Any]
    function_profiles: List[PerformanceProfile]
    bottlenecks: List[str]
    recommendations: List[str]
    resource_alerts: List[str]


class SystemResourceMonitor:
    """Monitor system resources in real - time"""

    def __init__(self, sample_interval: float = 1.0, history_size: int = 1000):
        """
        Initialize system resource monitor

        Args:
            sample_interval: Seconds between samples
            history_size: Number of samples to keep in history
        """
        self.sample_interval = sample_interval
        self.history = deque(maxlen=history_size)
        self.monitoring = False
        self.monitor_thread = None
        self._stop_event = threading.Event()

        # Resource thresholds for alerts
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0

        # Try to get system info, fallback gracefully
        self._get_system_info = self._create_system_info_getter()

    def _create_system_info_getter(self) -> Callable[[], Dict[str, Any]]:
        """Create system info getter with fallbacks"""
        try:
            import psutil

            def get_system_info():
                """TODO: Add docstring for get_system_info."""
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()

                return {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_mb": memory.used / (1024 * 1024),
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "disk_read_mb": (
                        disk_io.read_bytes / (1024 * 1024) if disk_io else 0
                    ),
                    "disk_write_mb": (
                        disk_io.write_bytes / (1024 * 1024) if disk_io else 0
                    ),
                    "network_sent_mb": (
                        net_io.bytes_sent / (1024 * 1024) if net_io else 0
                    ),
                    "network_recv_mb": (
                        net_io.bytes_recv / (1024 * 1024) if net_io else 0
                    ),
                    "process_count": len(psutil.pids()),
                    "load_average": (
                        psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0
                    ),
                }

            return get_system_info

        except ImportError:
            logger.warning("psutil not available, using mock system metrics")

            def get_mock_info():
                """TODO: Add docstring for get_mock_info."""
                return {
                    "cpu_percent": 25.0 + (time.time() % 10) * 5,  # Simulated load
                    "memory_percent": 40.0,
                    "memory_used_mb": 2048.0,
                    "memory_available_mb": 4096.0,
                    "disk_read_mb": 100.0,
                    "disk_write_mb": 50.0,
                    "network_sent_mb": 10.0,
                    "network_recv_mb": 20.0,
                    "process_count": 150,
                    "load_average": 1.5,
                }

            return get_mock_info

    def start_monitoring(self):
        """Start resource monitoring"""
        if self.monitoring:
            logger.warning("Resource monitoring already active")
            return

        self.monitoring = True
        self._stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("System resource monitoring started")

    def stop_monitoring(self):
        """Stop resource monitoring"""
        if not self.monitoring:
            return

        self.monitoring = False
        self._stop_event.set()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        logger.info("System resource monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                # Get system metrics
                info = self._get_system_info()

                metrics = SystemMetrics(timestamp=datetime.now(timezone.utc), **info)

                # Add to history
                self.history.append(metrics)

                # Check for alerts
                self._check_resource_alerts(metrics)

                # Wait for next sample
                self._stop_event.wait(self.sample_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self._stop_event.wait(self.sample_interval)

    def _check_resource_alerts(self, metrics: SystemMetrics):
        """Check for resource threshold violations"""
        alerts = []

        if metrics.cpu_percent > self.cpu_threshold:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        if metrics.memory_percent > self.memory_threshold:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")

        if alerts:
            logger.warning(f"Resource alerts: {', '.join(alerts)}")

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        return self.history[-1] if self.history else None

    def get_metrics_history(self, duration_minutes: int = 10) -> List[SystemMetrics]:
        """Get metrics history for specified duration"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
        return [m for m in self.history if m.timestamp >= cutoff_time]

    def get_metrics_summary(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """Get summary statistics for metrics"""
        history = self.get_metrics_history(duration_minutes)

        if not history:
            return {}

        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]

        return {
            "duration_minutes": duration_minutes,
            "sample_count": len(history),
            "cpu": {
                "average": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "current": history[-1].cpu_percent,
            },
            "memory": {
                "average": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "current": history[-1].memory_percent,
            },
            "alerts_triggered": len(
                [
                    m
                    for m in history
                    if m.cpu_percent > self.cpu_threshold
                    or m.memory_percent > self.memory_threshold
                ]
            ),
        }


class PerformanceProfiler:
    """Function - level performance profiler"""

    def __init__(self):
        """Initialize performance profiler"""
        self.profiles: Dict[str, PerformanceProfile] = {}
        self._lock = threading.Lock()
        self.enabled = True

    def profile(self, func_name: Optional[str] = None):
        """
        Decorator to profile function performance

        Args:
            func_name: Custom name for the function (default: use function.__name__)
        """

        def decorator(func):
            """TODO: Add docstring for decorator."""
            profile_name = func_name or func.__name__

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                """TODO: Add docstring for sync_wrapper."""
                if not self.enabled:
                    return func(*args, **kwargs)

                start_time = time.time()
                start_memory = self._get_memory_usage()

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    end_memory = self._get_memory_usage()

                    execution_time_ms = (end_time - start_time) * 1000
                    memory_delta = max(0, end_memory - start_memory)

                    self._record_profile(profile_name, execution_time_ms, memory_delta)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)

                start_time = time.time()
                start_memory = self._get_memory_usage()

                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    end_memory = self._get_memory_usage()

                    execution_time_ms = (end_time - start_time) * 1000
                    memory_delta = max(0, end_memory - start_memory)

                    self._record_profile(profile_name, execution_time_ms, memory_delta)

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0

    def _record_profile(
        self, func_name: str, execution_time_ms: float, memory_mb: float
    ):
        """Record performance profile data"""
        with self._lock:
            if func_name not in self.profiles:
                self.profiles[func_name] = PerformanceProfile(function_name=func_name)

            self.profiles[func_name].update(execution_time_ms, memory_mb)

    def get_profile(self, func_name: str) -> Optional[PerformanceProfile]:
        """Get profile for specific function"""
        return self.profiles.get(func_name)

    def get_all_profiles(self) -> List[PerformanceProfile]:
        """Get all function profiles"""
        return list(self.profiles.values())

    def get_slowest_functions(self, limit: int = 10) -> List[PerformanceProfile]:
        """Get slowest functions by average execution time"""
        return sorted(
            self.profiles.values(), key=lambda p: p.average_time_ms, reverse=True
        )[:limit]

    def get_most_called_functions(self, limit: int = 10) -> List[PerformanceProfile]:
        """Get most frequently called functions"""
        return sorted(self.profiles.values(), key=lambda p: p.call_count, reverse=True)[
            :limit
        ]

    def reset_profiles(self):
        """Reset all performance profiles"""
        with self._lock:
            self.profiles.clear()
        logger.info("Performance profiles reset")

    def enable(self):
        """Enable profiling"""
        self.enabled = True

    def disable(self):
        """Disable profiling"""
        self.enabled = False


class ResourceMonitor:
    """
    Main resource monitoring coordinator
    """

    def __init__(self, sample_interval: float = 1.0):
        """
        Initialize resource monitor

        Args:
            sample_interval: Seconds between resource samples
        """
        self.system_monitor = SystemResourceMonitor(sample_interval)
        self.performance_profiler = PerformanceProfiler()
        self.start_time = None
        self.alerts = []

        logger.info("Resource monitor initialized")

    def start_monitoring(self):
        """Start comprehensive monitoring"""
        self.start_time = datetime.now(timezone.utc)
        self.system_monitor.start_monitoring()
        self.performance_profiler.enable()

        logger.info("Comprehensive resource monitoring started")

    def stop_monitoring(self):
        """Stop comprehensive monitoring"""
        self.system_monitor.stop_monitoring()
        self.performance_profiler.disable()

        logger.info("Comprehensive resource monitoring stopped")

    def profile_function(self, func_name: Optional[str] = None):
        """Get function profiling decorator"""
        return self.performance_profiler.profile(func_name)

    async def monitor_operation(
        self, operation_name: str, operation_func: Callable, *args, **kwargs
    ):
        """
        Monitor a specific operation

        Args:
            operation_name: Name of the operation
            operation_func: Function to monitor
            *args, **kwargs: Arguments for the function

        Returns:
            Operation result
        """
        # Apply profiling
        profiled_func = self.performance_profiler.profile(operation_name)(
            operation_func
        )

        # Record system state before operation
        start_metrics = self.system_monitor.get_current_metrics()

        # Execute operation
        if asyncio.iscoroutinefunction(operation_func):
            result = await profiled_func(*args, **kwargs)
        else:
            result = profiled_func(*args, **kwargs)

        # Record system state after operation
        end_metrics = self.system_monitor.get_current_metrics()

        # Log operation impact
        if start_metrics and end_metrics:
            cpu_delta = end_metrics.cpu_percent - start_metrics.cpu_percent
            memory_delta = end_metrics.memory_percent - start_metrics.memory_percent

            if abs(cpu_delta) > 10 or abs(memory_delta) > 5:
                logger.info(
                    f"Operation '{operation_name}' impact: CPU {cpu_delta:+.1f}%, Memory {memory_delta:+.1f}%"
                )

        return result

    def get_performance_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        # Check slowest functions
        slow_functions = self.performance_profiler.get_slowest_functions(5)
        for func in slow_functions:
            if func.average_time_ms > 1000:  # Slower than 1 second
                bottlenecks.append(
                    f"Slow function: {func.function_name} ({func.average_time_ms:.0f}ms avg)"
                )

        # Check system resources
        current_metrics = self.system_monitor.get_current_metrics()
        if current_metrics:
            if current_metrics.cpu_percent > 80:
                bottlenecks.append(
                    f"High CPU usage: {current_metrics.cpu_percent:.1f}%"
                )

            if current_metrics.memory_percent > 85:
                bottlenecks.append(
                    f"High memory usage: {current_metrics.memory_percent:.1f}%"
                )

        # Check frequently called functions
        frequent_functions = self.performance_profiler.get_most_called_functions(3)
        for func in frequent_functions:
            if func.call_count > 1000 and func.average_time_ms > 100:
                bottlenecks.append(
                    f"Frequent slow function: {func.function_name} ({func.call_count} calls)"
                )

        return bottlenecks

    def get_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []

        # System - level recommendations
        metrics_summary = self.system_monitor.get_metrics_summary(10)
        if metrics_summary:
            if metrics_summary["cpu"]["average"] > 70:
                recommendations.append("Consider optimizing CPU - intensive operations")

            if metrics_summary["memory"]["average"] > 80:
                recommendations.append(
                    "Implement memory optimization or increase available memory"
                )

            if metrics_summary.get("alerts_triggered", 0) > 5:
                recommendations.append(
                    "Frequent resource alerts - review system capacity"
                )

        # Function - level recommendations
        slow_functions = self.performance_profiler.get_slowest_functions(3)
        for func in slow_functions:
            if func.average_time_ms > 500:
                recommendations.append(f"Optimize slow function: {func.function_name}")

        # General recommendations
        recommendations.extend(
            [
                "Use asynchronous programming for I / O operations",
                "Implement caching for frequently accessed data",
                "Consider parallel processing for CPU - intensive tasks",
                "Monitor and optimize database queries",
                "Use connection pooling for external services",
            ]
        )

        return recommendations[:10]  # Limit to top 10

    def generate_performance_report(self) -> PerformanceReport:
        """Generate comprehensive performance report"""
        if not self.start_time:
            raise ValueError("Monitoring must be started before generating report")

        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        # System metrics summary
        system_summary = self.system_monitor.get_metrics_summary(10)

        # Function profiles
        function_profiles = self.performance_profiler.get_all_profiles()

        # Bottlenecks and recommendations
        bottlenecks = self.get_performance_bottlenecks()
        recommendations = self.get_optimization_recommendations()

        # Resource alerts
        resource_alerts = []
        current_metrics = self.system_monitor.get_current_metrics()
        if current_metrics:
            if current_metrics.cpu_percent > 80:
                resource_alerts.append(f"High CPU: {current_metrics.cpu_percent:.1f}%")
            if current_metrics.memory_percent > 85:
                resource_alerts.append(
                    f"High Memory: {current_metrics.memory_percent:.1f}%"
                )

        return PerformanceReport(
            report_id=f"perf_report_{int(time.time())}",
            generated_at=datetime.now(timezone.utc),
            duration_seconds=duration,
            system_metrics_summary=system_summary,
            function_profiles=function_profiles,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            resource_alerts=resource_alerts,
        )

    def get_live_metrics(self) -> Dict[str, Any]:
        """Get current live metrics"""
        current_metrics = self.system_monitor.get_current_metrics()
        recent_profiles = self.performance_profiler.get_slowest_functions(5)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": current_metrics.cpu_percent if current_metrics else 0,
                "memory_percent": (
                    current_metrics.memory_percent if current_metrics else 0
                ),
                "memory_used_mb": (
                    current_metrics.memory_used_mb if current_metrics else 0
                ),
            },
            "performance": {
                "total_functions_profiled": len(self.performance_profiler.profiles),
                "slowest_function": (
                    recent_profiles[0].function_name if recent_profiles else None
                ),
                "slowest_time_ms": (
                    recent_profiles[0].average_time_ms if recent_profiles else 0
                ),
            },
            "monitoring_duration_seconds": (
                (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
        }


# Example usage and testing functions
async def demo_resource_monitor():
    """Demonstrate resource monitoring capabilities"""
    print("📊 Resource Monitor Demo")
    print("=" * 30)

    # Initialize monitor
    monitor = ResourceMonitor(sample_interval=0.5)

    # Start monitoring
    monitor.start_monitoring()

    print("🚀 Monitoring started, running sample operations...")

    # Example operations to monitor
    @monitor.profile_function("cpu_intensive_task")
    def cpu_intensive_task(n: int) -> int:
        """Simulate CPU - intensive work"""
        result = 0
        for i in range(n):
            result += i * i
        return result

    @monitor.profile_function("io_simulation")
    async def io_simulation(delay: float) -> str:
        """Simulate I / O operation"""
        await asyncio.sleep(delay)
        return f"IO completed after {delay}s"

    # Run operations
    time.time()

    # CPU intensive operations
    for _ in range(5):
        cpu_intensive_task(100000)

    # I / O operations
    await io_simulation(0.1)
    await io_simulation(0.2)

    # Monitor a complex operation
    await monitor.monitor_operation(
        "complex_operation", lambda: time.sleep(0.1) or "Complex task done"
    )

    # Wait to collect some metrics
    await asyncio.sleep(2)

    # Get live metrics
    live_metrics = monitor.get_live_metrics()
    print("\n📊 Live Metrics:")
    print(f"   CPU: {live_metrics['system']['cpu_percent']:.1f}%")
    print(f"   Memory: {live_metrics['system']['memory_percent']:.1f}%")
    print(
        "   Functions profiled: "
        f"{live_metrics['performance']['total_functions_profiled']}"
    )

    # Get performance bottlenecks
    bottlenecks = monitor.get_performance_bottlenecks()
    if bottlenecks:
        print("\n⚠️  Performance Bottlenecks:")
        for bottleneck in bottlenecks[:3]:
            print(f"   • {bottleneck}")

    # Generate comprehensive report
    report = monitor.generate_performance_report()

    print("\n📋 Performance Report:")
    print(f"   Monitoring duration: {report.duration_seconds:.1f}s")
    print(f"   Function profiles: {len(report.function_profiles)}")
    print(f"   Bottlenecks identified: {len(report.bottlenecks)}")
    print(f"   Recommendations: {len(report.recommendations)}")

    if report.function_profiles:
        print("\n🏆 Top Function Performance:")
        top_profiles = sorted(
            report.function_profiles, key=lambda p: p.average_time_ms, reverse=True
        )[:3]
        for profile in top_profiles:
            print(
                f"   • {profile.function_name}: {profile.average_time_ms:.2f}ms avg ({profile.call_count} calls)"
            )

    # Stop monitoring
    monitor.stop_monitoring()

    return monitor


if __name__ == "__main__":
    asyncio.run(demo_resource_monitor())
