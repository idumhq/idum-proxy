import asyncio
import logging

from starlette.requests import Request
from starlette.responses import Response

from idum_proxy.config.models import Endpoint, Backends
from idum_proxy.networking.connection_pooling.connection_pooling import (
    ConnectionPooling,
)

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        connection_pooling: ConnectionPooling,
        endpoint: Endpoint,
        backend: Backends,
    ):
        self.endpoint = endpoint
        self.backend = backend
        self.connection_pooling = connection_pooling
        self.jobs: dict[str, dict] = {}

    async def handle_request(self, request: Request, headers: dict) -> Response:
        # the request returns the status of scheduler
        path = request.url.path.removeprefix(self.endpoint.prefix)
        if path == "/status" and request.method == "GET":
            return Response("get status")
        elif path == "/history" and request.method == "GET":
            return Response("get history")
        return Response("list")

    """
    POST /jobs          # Create new scheduled job
    GET /jobs           # List all jobs
    GET /jobs/{job_id}  # Get job status
    PUT /jobs/{job_id}  # Update job configuration
    DELETE /jobs/{job_id} # Remove job
    """


class JobHistoryStorage:
    def __init__(self, path: str, retention_hours: int = 168):
        self.path = Path(path)
        self.retention_hours = retention_hours
        self.path.mkdir(parents=True, exist_ok=True)

    async def save_job_result(self, job_id: str, result: dict[str, Any]) -> None:
        """Save job execution result to file storage"""
        timestamp = datetime.now().isoformat()
        job_file = self.path / f"{job_id}_{timestamp.replace(':', '-')}.json"

        job_data = {"job_id": job_id, "timestamp": timestamp, "result": result}

        try:
            with open(job_file, "w") as f:
                json.dump(job_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job history for {job_id}: {e}")

    async def cleanup_old_records(self) -> None:
        """Remove job history files older than retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        for file_path in self.path.glob("*.json"):
            try:
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.info(f"Removed old job history file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup job history file {file_path}: {e}")

    async def get_job_history(
        self, job_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve job history records"""
        history = []
        pattern = f"{job_id}_*.json" if job_id else "*.json"

        for file_path in sorted(
            self.path.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            if len(history) >= limit:
                break

            try:
                with open(file_path, "r") as f:
                    job_data = json.load(f)
                    history.append(job_data)
            except Exception as e:
                logger.error(f"Failed to read job history file {file_path}: {e}")

        return history


class SchedulerService:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.job_history = JobHistoryStorage(
            path=config["job_history"]["path"],
            retention_hours=config["job_history"]["retention_hours"],
        )

    async def execute_command(
        self, job_id: str, command: str, description: str
    ) -> None:
        """Execute a scheduled command and log the result"""
        start_time = datetime.now()
        logger.info(f"Starting job {job_id}: {description}")

        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            result = {
                "job_id": job_id,
                "command": command,
                "description": description,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "return_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "success": process.returncode == 0,
            }

            await self.job_history.save_job_result(job_id, result)

            if process.returncode == 0:
                logger.info(f"Job {job_id} completed successfully")
            else:
                logger.error(
                    f"Job {job_id} failed with return code {process.returncode}"
                )

        except Exception as e:
            result = {
                "job_id": job_id,
                "command": command,
                "description": description,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "error": str(e),
                "success": False,
            }

            await self.job_history.save_job_result(job_id, result)
            logger.error(f"Job {job_id} failed with exception: {e}")

    async def start(self) -> None:
        """Start the scheduler and register cron jobs"""
        # Add cron jobs from config
        for job_id, job_config in self.config["cron_jobs"].items():
            schedule = job_config["schedule"]
            command = job_config["command"]
            description = job_config["description"]

            # Parse cron schedule (minute, hour, day, month, day_of_week)
            cron_parts = schedule.split()
            if len(cron_parts) == 5:
                trigger = CronTrigger(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4],
                )

                self.scheduler.add_job(
                    self.execute_command,
                    trigger=trigger,
                    args=[job_id, command, description],
                    id=job_id,
                    max_instances=1,
                    coalesce=True,
                )

                logger.info(f"Registered cron job {job_id}: {description} ({schedule})")

        # Add cleanup job for job history
        cleanup_trigger = CronTrigger(hour=3, minute=0)  # Daily at 3 AM
        self.scheduler.add_job(
            self.job_history.cleanup_old_records,
            trigger=cleanup_trigger,
            id="job_history_cleanup",
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.start()
        logger.info("Scheduler started successfully")

    async def stop(self) -> None:
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    async def get_jobs(self) -> list[dict[str, Any]]:
        """Get list of scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs
