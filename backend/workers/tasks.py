"""Celery tasks para processamento assíncrono."""

import asyncio

import structlog
from celery import Celery

from config import settings

logger = structlog.get_logger()

celery_app = Celery(
    "clovisai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora max por task
    task_soft_time_limit=3000,  # Soft limit de 50 min
    worker_max_tasks_per_child=10,  # Reinicia worker após 10 tasks (libera memória GPU)
    worker_concurrency=settings.max_concurrent_jobs,
)


def _run_async(coro):
    """Utilitário para rodar coroutines dentro de tasks Celery."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="pipeline.full")
def run_full_pipeline(self, project_id: str) -> dict:
    """Executa o pipeline completo de processamento."""
    logger.info("celery_pipeline_full", project_id=project_id, task_id=self.request.id)

    async def _execute():
        from database import async_session
        from services.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        async with async_session() as db:
            await orchestrator.run_full_pipeline(project_id, db)

    _run_async(_execute())
    return {"project_id": project_id, "status": "completed"}


@celery_app.task(bind=True, name="pipeline.step")
def run_pipeline_step(self, project_id: str, step: str) -> dict:
    """Executa um passo específico do pipeline."""
    logger.info(
        "celery_pipeline_step",
        project_id=project_id,
        step=step,
        task_id=self.request.id,
    )

    async def _execute():
        from database import async_session
        from models.project import PipelineStep
        from services.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        async with async_session() as db:
            project = await db.get(
                __import__("models.project", fromlist=["Project"]).Project,
                project_id,
            )
            if project:
                pipeline_step = PipelineStep(step)
                await orchestrator.run_step(project, pipeline_step, db)

    _run_async(_execute())
    return {"project_id": project_id, "step": step, "status": "completed"}
