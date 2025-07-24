"""
Parallel Processing Optimization
===============================

High - performance parallel processing for systematic review tasks.

This module provides:
- Multi - core task processing
- Asynchronous batch processing
- Load balancing and task distribution
- Intelligent scheduling

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import logging
import queue
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Try to import psutil, fallback gracefully
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

    # Mock psutil functions for basic functionality
    class MockPSUtil:
        """TODO: Add class docstring for MockPSUtil."""

        @staticmethod
        def cpu_count():
            """TODO: Add docstring for cpu_count."""
            return 4

        @staticmethod
        def cpu_percent(interval=0.1):
            """TODO: Add docstring for cpu_percent."""
            return 50.0

        @staticmethod
        def virtual_memory():
            """TODO: Add docstring for virtual_memory."""

            class MockMemory:
                """TODO: Add class docstring for MockMemory."""

                percent = 50.0
                available = 1024 * 1024 * 1024  # 1GB

            return MockMemory()

        @staticmethod
        def disk_io_counters():
            """TODO: Add docstring for disk_io_counters."""
            return None

        @staticmethod
        def net_io_counters():
            """TODO: Add docstring for net_io_counters."""

            class MockNetIO:
                """TODO: Add class docstring for MockNetIO."""

                def _asdict(self):
                    return {"bytes_sent": 0, "bytes_recv": 0}

            return MockNetIO()

        @staticmethod
        def pids():
            """TODO: Add docstring for pids."""
            return list(range(100))  # Mock 100 processes

    psutil = MockPSUtil()

# Configure logging
logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """Processing strategy options"""

    SEQUENTIAL = "sequential"
    THREAD_POOL = "thread_pool"
    PROCESS_POOL = "process_pool"
    ASYNC_BATCH = "async_batch"
    HYBRID = "hybrid"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ParallelConfig:
    """Configuration for parallel processing"""

    max_workers: Optional[int] = None
    strategy: ProcessingStrategy = ProcessingStrategy.HYBRID
    batch_size: int = 100
    timeout_seconds: int = 300
    memory_limit_mb: int = 1024
    cpu_threshold: float = 0.8
    enable_profiling: bool = False
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class Task:
    """Individual processing task"""

    task_id: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None


@dataclass
class TaskBatch:
    """Batch of related tasks"""

    batch_id: str
    tasks: List[Task]
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_duration: Optional[float] = None


@dataclass
class ProcessingResult:
    """Result of parallel processing operation"""

    batch_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_duration: float
    average_task_time: float
    success_rate: float
    results: List[Any]
    errors: List[Exception]
    performance_metrics: Dict[str, Any]


class ResourceMonitor:
    """Monitor system resources during processing"""

    def __init__(self):
        self.start_time = None
        self.metrics_history = []
        self.monitoring = False

    def start_monitoring(self):
        """Start resource monitoring"""
        self.start_time = time.time()
        self.monitoring = True
        self.metrics_history = []

    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        net_io = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_io": (
                disk_io._asdict() if disk_io and hasattr(disk_io, "_asdict") else {}
            ),
            "network_io": net_io._asdict() if hasattr(net_io, "_asdict") else {},
            "process_count": len(psutil.pids()),
            "timestamp": time.time(),
        }

    def record_metrics(self):
        """Record current metrics to history"""
        if self.monitoring:
            metrics = self.get_current_metrics()
            self.metrics_history.append(metrics)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary"""
        if not self.metrics_history:
            return {}

        cpu_values = [m["cpu_percent"] for m in self.metrics_history]
        memory_values = [m["memory_percent"] for m in self.metrics_history]

        return {
            "monitoring_duration": (
                time.time() - self.start_time if self.start_time else 0
            ),
            "cpu_avg": sum(cpu_values) / len(cpu_values),
            "cpu_max": max(cpu_values),
            "memory_avg": sum(memory_values) / len(memory_values),
            "memory_max": max(memory_values),
            "samples_collected": len(self.metrics_history),
        }


class TaskScheduler:
    """Intelligent task scheduler with priority and dependency management"""

    def __init__(self):
        self.task_queue = queue.PriorityQueue()
        self.dependency_graph = {}
        self.completed_tasks = set()
        self.running_tasks = set()

    def add_task(self, task: Task):
        """Add task to scheduler"""
        # Priority queue uses negative priority for max - heap behavior
        priority_value = -task.priority.value
        self.task_queue.put((priority_value, task.created_at.timestamp(), task))

    def add_batch(self, batch: TaskBatch):
        """Add batch of tasks with dependencies"""
        # Register dependencies
        if batch.dependencies:
            self.dependency_graph[batch.batch_id] = batch.dependencies

        # Add all tasks
        for task in batch.tasks:
            self.add_task(task)

    def get_next_task(self) -> Optional[Task]:
        """Get next available task respecting dependencies"""
        if self.task_queue.empty():
            return None

        # Check if we can execute the highest priority task
        try:
            priority, timestamp, task = self.task_queue.get_nowait()

            # Check if dependencies are satisfied
            if self._dependencies_satisfied(task):
                self.running_tasks.add(task.task_id)
                return task
            else:
                # Put it back and try again later
                self.task_queue.put((priority, timestamp, task))
                return None

        except queue.Empty:
            return None

    def mark_completed(self, task_id: str):
        """Mark task as completed"""
        self.completed_tasks.add(task_id)
        self.running_tasks.discard(task_id)

    def _dependencies_satisfied(self, task: Task) -> bool:
        """Check if task dependencies are satisfied"""
        # For now, simplified dependency checking
        # In a full implementation, this would check batch dependencies
        return True


class ParallelProcessor:
    """
    High - performance parallel processor for systematic review tasks
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        """
        Initialize parallel processor

        Args:
            config: Processing configuration
        """
        self.config = config or ParallelConfig()
        self.scheduler = TaskScheduler()
        self.resource_monitor = ResourceMonitor()
        self.active_executors = {}

        # Determine optimal worker count
        if self.config.max_workers is None:
            self.config.max_workers = min(32, (psutil.cpu_count() or 4) + 4)

        logger.info(
            f"Parallel processor initialized with {self.config.max_workers} max workers"
        )

    async def process_batch(self, batch: TaskBatch) -> ProcessingResult:
        """
        Process a batch of tasks in parallel

        Args:
            batch: Batch of tasks to process

        Returns:
            Processing results
        """
        start_time = time.time()
        self.resource_monitor.start_monitoring()

        logger.info(
            f"Starting batch processing: {batch.batch_id} ({len(batch.tasks)} tasks)"
        )

        try:
            # Choose processing strategy
            strategy = self._choose_strategy(batch)
            logger.info(f"Using processing strategy: {strategy.value}")

            # Process based on strategy
            if strategy == ProcessingStrategy.ASYNC_BATCH:
                results = await self._process_async_batch(batch)
            elif strategy == ProcessingStrategy.THREAD_POOL:
                results = await self._process_thread_pool(batch)
            elif strategy == ProcessingStrategy.PROCESS_POOL:
                results = await self._process_process_pool(batch)
            elif strategy == ProcessingStrategy.HYBRID:
                results = await self._process_hybrid(batch)
            else:
                results = await self._process_sequential(batch)

            # Calculate metrics
            end_time = time.time()
            total_duration = end_time - start_time

            completed_count = sum(1 for r in results if r.get("status") == "completed")
            failed_count = len(results) - completed_count

            # Filter errors properly
            error_list = []
            for r in results:
                error = r.get("error")
                if error and isinstance(error, Exception):
                    error_list.append(error)

            result = ProcessingResult(
                batch_id=batch.batch_id,
                total_tasks=len(batch.tasks),
                completed_tasks=completed_count,
                failed_tasks=failed_count,
                total_duration=total_duration,
                average_task_time=(
                    total_duration / len(batch.tasks) if batch.tasks else 0
                ),
                success_rate=completed_count / len(batch.tasks) if batch.tasks else 0,
                results=[r.get("result") for r in results],
                errors=error_list,
                performance_metrics=self.resource_monitor.get_performance_summary(),
            )

            logger.info(
                f"Batch processing completed: {completed_count}/{len(batch.tasks)} tasks successful"
            )
            return result

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
        finally:
            self.resource_monitor.stop_monitoring()

    def _choose_strategy(self, batch: TaskBatch) -> ProcessingStrategy:
        """Choose optimal processing strategy based on batch characteristics"""
        task_count = len(batch.tasks)

        # Get system metrics
        cpu_count = psutil.cpu_count() or 4
        memory_available = psutil.virtual_memory().available / (1024 * 1024)  # MB

        # Strategy selection logic
        if task_count <= 10:
            return ProcessingStrategy.SEQUENTIAL
        elif task_count <= 50 and memory_available > 2048:
            return ProcessingStrategy.THREAD_POOL
        elif task_count > 100 and cpu_count >= 8:
            return ProcessingStrategy.HYBRID
        elif memory_available > 4096:
            return ProcessingStrategy.PROCESS_POOL
        else:
            return ProcessingStrategy.ASYNC_BATCH

    async def _process_async_batch(self, batch: TaskBatch) -> List[Dict[str, Any]]:
        """Process batch using asyncio for I / O bound tasks"""

        async def execute_task(task: Task) -> Dict[str, Any]:
            try:
                task.started_at = datetime.now(timezone.utc)
                task.status = TaskStatus.RUNNING

                # Execute task with timeout
                if asyncio.iscoroutinefunction(task.function):
                    if task.timeout:
                        result = await asyncio.wait_for(
                            task.function(*task.args, **task.kwargs),
                            timeout=task.timeout,
                        )
                    else:
                        result = await task.function(*task.args, **task.kwargs)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: task.function(*task.args, **task.kwargs)
                    )

                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)

                return {
                    "task_id": task.task_id,
                    "status": "completed",
                    "result": result,
                    "duration": (task.completed_at - task.started_at).total_seconds(),
                }

            except Exception as e:
                task.error = e
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)

                logger.error(f"Task {task.task_id} failed: {e}")
                return {
                    "task_id": task.task_id,
                    "status": "failed",
                    "error": e,
                    "duration": (task.completed_at - task.started_at).total_seconds(),
                }

        # Process tasks in controlled batches to avoid overwhelming system
        max_workers = self.config.max_workers or 4
        batch_size = min(self.config.batch_size, max_workers)
        results = []

        for i in range(0, len(batch.tasks), batch_size):
            batch_chunk = batch.tasks[i:i + batch_size]
            chunk_results = await asyncio.gather(
                *[execute_task(task) for task in batch_chunk], return_exceptions=True
            )
            results.extend(
                [
                    r if isinstance(r, dict) else {"status": "failed", "error": r}
                    for r in chunk_results
                ]
            )

        return results

    async def _process_thread_pool(self, batch: TaskBatch) -> List[Dict[str, Any]]:
        """Process batch using thread pool for I / O bound tasks"""

        def execute_task_sync(task: Task) -> Dict[str, Any]:
            """TODO: Add docstring for execute_task_sync."""
            try:
                task.started_at = datetime.now(timezone.utc)
                task.status = TaskStatus.RUNNING

                result = task.function(*task.args, **task.kwargs)

                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)

                return {
                    "task_id": task.task_id,
                    "status": "completed",
                    "result": result,
                    "duration": (task.completed_at - task.started_at).total_seconds(),
                }

            except Exception as e:
                task.error = e
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)

                return {
                    "task_id": task.task_id,
                    "status": "failed",
                    "error": e,
                    "duration": (task.completed_at - task.started_at).total_seconds(),
                }

        results = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, execute_task_sync, task)
                for task in batch.tasks
            ]

            completed_futures = await asyncio.gather(*futures, return_exceptions=True)
            results = [
                f if isinstance(f, dict) else {"status": "failed", "error": f}
                for f in completed_futures
            ]

        return results

    async def _process_process_pool(self, batch: TaskBatch) -> List[Dict[str, Any]]:
        """Process batch using process pool for CPU bound tasks"""

        def execute_task_process(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """TODO: Add docstring for execute_task_process."""
            try:
                start_time = datetime.now(timezone.utc)
                function = task_data["function"]
                args = task_data["args"]
                kwargs = task_data["kwargs"]

                result = function(*args, **kwargs)

                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()

                return {
                    "task_id": task_data["task_id"],
                    "status": "completed",
                    "result": result,
                    "duration": duration,
                }

            except Exception as e:
                return {
                    "task_id": task_data["task_id"],
                    "status": "failed",
                    "error": str(e),  # Serialize exception
                    "duration": 0,
                }

        # Prepare task data for process pool (must be pickleable)
        task_data_list = []
        for task in batch.tasks:
            task_data_list.append(
                {
                    "task_id": task.task_id,
                    "function": task.function,
                    "args": task.args,
                    "kwargs": task.kwargs,
                }
            )

        results = []
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, execute_task_process, task_data)
                for task_data in task_data_list
            ]

            completed_futures = await asyncio.gather(*futures, return_exceptions=True)
            results = [
                f if isinstance(f, dict) else {"status": "failed", "error": str(f)}
                for f in completed_futures
            ]

        return results

    async def _process_hybrid(self, batch: TaskBatch) -> List[Dict[str, Any]]:
        """Process batch using hybrid approach - mix of async and thread pool"""
        # Categorize tasks by type (I / O vs CPU bound)
        io_tasks = []
        cpu_tasks = []

        for task in batch.tasks:
            # Simple heuristic: if function name suggests I / O, use async
            func_name = getattr(task.function, "__name__", "").lower()
            if any(
                keyword in func_name
                for keyword in [
                    "fetch",
                    "request",
                    "download",
                    "upload",
                    "read",
                    "write",
                ]
            ):
                io_tasks.append(task)
            else:
                cpu_tasks.append(task)

        results = []

        # Process I / O tasks asynchronously
        if io_tasks:
            io_batch = TaskBatch(
                batch_id=f"{batch.batch_id}_io", tasks=io_tasks, priority=batch.priority
            )
            io_results = await self._process_async_batch(io_batch)
            results.extend(io_results)

        # Process CPU tasks in thread pool
        if cpu_tasks:
            cpu_batch = TaskBatch(
                batch_id=f"{batch.batch_id}_cpu",
                tasks=cpu_tasks,
                priority=batch.priority,
            )
            cpu_results = await self._process_thread_pool(cpu_batch)
            results.extend(cpu_results)

        return results

    async def _process_sequential(self, batch: TaskBatch) -> List[Dict[str, Any]]:
        """Process batch sequentially (fallback strategy)"""
        results = []

        for task in batch.tasks:
            try:
                task.started_at = datetime.now(timezone.utc)
                task.status = TaskStatus.RUNNING

                result = task.function(*task.args, **task.kwargs)

                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)

                results.append(
                    {
                        "task_id": task.task_id,
                        "status": "completed",
                        "result": result,
                        "duration": (
                            task.completed_at - task.started_at
                        ).total_seconds(),
                    }
                )

            except Exception as e:
                task.error = e
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)

                results.append(
                    {
                        "task_id": task.task_id,
                        "status": "failed",
                        "error": e,
                        "duration": (
                            task.completed_at - task.started_at
                        ).total_seconds(),
                    }
                )

        return results

    async def process_literature_screening(
        self, studies: List[Dict[str, Any]]
    ) -> ProcessingResult:
        """
        Optimized literature screening processing

        Args:
            studies: List of studies to screen

        Returns:
            Processing results
        """
        # Create screening tasks
        tasks = []
        for i, study in enumerate(studies):
            task = Task(
                task_id=f"screen_{i}",
                function=self._screen_study,
                args=(study,),
                priority=TaskPriority.HIGH,
            )
            tasks.append(task)

        # Create batch
        batch = TaskBatch(
            batch_id=f"literature_screening_{int(time.time())}",
            tasks=tasks,
            priority=TaskPriority.HIGH,
        )

        return await self.process_batch(batch)

    def _screen_study(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Screen individual study (example implementation)"""
        # Simulate screening logic
        time.sleep(0.1)  # Simulate processing time

        # Simple screening logic based on title / abstract
        title = study.get("title", "").lower()
        abstract = study.get("abstract", "").lower()

        # Example criteria
        relevant_keywords = [
            "machine learning",
            "ai",
            "artificial intelligence",
            "systematic review",
        ]
        exclusion_keywords = ["case study", "editorial", "letter"]

        score = 0
        for keyword in relevant_keywords:
            if keyword in title or keyword in abstract:
                score += 1

        for keyword in exclusion_keywords:
            if keyword in title or keyword in abstract:
                score -= 2

        decision = "include" if score > 0 else "exclude"

        return {
            "study_id": study.get("id"),
            "decision": decision,
            "confidence": min(abs(score) / len(relevant_keywords), 1.0),
            "reasoning": f"Score: {score} based on keyword analysis",
        }


# Example utility functions for creating common task patterns
def create_literature_screening_batch(
    studies: List[Dict[str, Any]], batch_size: int = 100
) -> List[TaskBatch]:
    """Create optimized batches for literature screening"""
    batches = []

    for i in range(0, len(studies), batch_size):
        batch_studies = studies[i:i + batch_size]
        tasks = []

        for j, study in enumerate(batch_studies):
            task = Task(
                task_id=f"screen_{i + j}",
                function=lambda s: {
                    "study_id": s.get("id"),
                    "decision": "include",
                },  # Placeholder
                args=(study,),
                priority=TaskPriority.NORMAL,
            )
            tasks.append(task)

        batch = TaskBatch(
            batch_id=f"screening_batch_{i // batch_size}",
            tasks=tasks,
            priority=TaskPriority.NORMAL,
        )
        batches.append(batch)

    return batches


async def demo_parallel_processing():
    """Demonstrate parallel processing capabilities"""
    print("🚀 Parallel Processing Demo")
    print("=" * 40)

    # Initialize processor
    config = ParallelConfig(
        max_workers=8, strategy=ProcessingStrategy.HYBRID, batch_size=50
    )
    processor = ParallelProcessor(config)

    # Create sample tasks
    def sample_task(task_id: int, duration: float = 0.1) -> Dict[str, Any]:
        """TODO: Add docstring for sample_task."""
        time.sleep(duration)
        return {
            "task_id": task_id,
            "result": f"Task {task_id} completed",
            "timestamp": time.time(),
        }

    tasks = []
    for i in range(100):
        task = Task(
            task_id=f"task_{i}",
            function=sample_task,
            args=(i, 0.05),
            priority=TaskPriority.NORMAL,
        )
        tasks.append(task)

    # Create batch
    batch = TaskBatch(batch_id="demo_batch", tasks=tasks)

    print(f"Processing {len(tasks)} tasks...")
    time.time()

    result = await processor.process_batch(batch)

    time.time()

    print("\n📊 Results:")
    print(f"   Total tasks: {result.total_tasks}")
    print(f"   Completed: {result.completed_tasks}")
    print(f"   Failed: {result.failed_tasks}")
    print(f"   Success rate: {result.success_rate:.1%}")
    print(f"   Total duration: {result.total_duration:.2f}s")
    print(f"   Average task time: {result.average_task_time:.3f}s")

    if result.performance_metrics:
        print(f"   CPU usage: {result.performance_metrics.get('cpu_avg', 0):.1f}%")
        print(
            f"   Memory usage: {result.performance_metrics.get('memory_avg', 0):.1f}%"
        )

    return processor


if __name__ == "__main__":
    asyncio.run(demo_parallel_processing())
