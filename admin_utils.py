"""
Admin utilities for Chess Elegante
Provides admin authentication and background job management
"""
from functools import wraps
from flask import abort
from flask_login import current_user
import threading
import queue
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def admin_required(f):
    """
    Decorator to restrict access to admin users only
    Usage: @admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401, "Authentication required")
        if not current_user.is_admin:
            abort(403, "Admin privileges required")
        return f(*args, **kwargs)
    return decorated_function


class BackgroundJobManager:
    """
    Simple background job manager for async tasks
    Uses threading to run jobs without blocking the main application
    """

    def __init__(self):
        self.jobs = {}  # job_id -> job_info
        self.job_queue = queue.Queue()
        self.worker_thread = None
        self._start_worker()

    def _start_worker(self):
        """Start background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            logger.info("Background job worker started")

    def _worker(self):
        """Worker thread that processes jobs from the queue"""
        while True:
            try:
                job_id, func, args, kwargs = self.job_queue.get()
                self._run_job(job_id, func, args, kwargs)
                self.job_queue.task_done()
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

    def _run_job(self, job_id, func, args, kwargs):
        """Execute a single job and update its status"""
        try:
            logger.info(f"Starting job {job_id}")
            self.jobs[job_id]['status'] = 'processing'
            self.jobs[job_id]['started_at'] = datetime.utcnow()

            result = func(*args, **kwargs)

            self.jobs[job_id]['status'] = 'completed'
            self.jobs[job_id]['completed_at'] = datetime.utcnow()
            self.jobs[job_id]['result'] = result
            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            self.jobs[job_id]['status'] = 'failed'
            self.jobs[job_id]['error'] = str(e)
            self.jobs[job_id]['completed_at'] = datetime.utcnow()

    def submit_job(self, job_id, func, *args, **kwargs):
        """
        Submit a job to be executed in the background

        Args:
            job_id: Unique identifier for the job (e.g., game_id)
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function

        Returns:
            job_id
        """
        self.jobs[job_id] = {
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None
        }

        self.job_queue.put((job_id, func, args, kwargs))
        logger.info(f"Job {job_id} submitted to queue")
        return job_id

    def get_job_status(self, job_id):
        """Get the current status of a job"""
        return self.jobs.get(job_id, {'status': 'not_found'})

    def cancel_job(self, job_id):
        """
        Cancel a pending job (cannot cancel running jobs)
        Note: This is a simple implementation and doesn't remove from queue
        """
        if job_id in self.jobs and self.jobs[job_id]['status'] == 'pending':
            self.jobs[job_id]['status'] = 'cancelled'
            return True
        return False


# Global job manager instance
job_manager = BackgroundJobManager()
