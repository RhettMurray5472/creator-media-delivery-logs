"""HTTP routes for a creator-media delivery workflow."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .infrai_logs import InfraiError, InfraiLogs


class MediaJobRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    source_format: Literal["mov", "mp4", "webm"]
    delivery_format: Literal["mp4", "webm"]


class MediaJobResult(BaseModel):
    asset_id: str
    order_id: str
    state: Literal["queued_for_transcode", "ready_for_creator"]


def get_logs() -> InfraiLogs:
    return InfraiLogs()


def decide_delivery(job: MediaJobRequest) -> MediaJobResult:
    """A matching source can be delivered without another transcode step."""
    return MediaJobResult(
        asset_id=job.asset_id,
        order_id=job.order_id,
        state=(
            "ready_for_creator"
            if job.source_format == job.delivery_format
            else "queued_for_transcode"
        ),
    )


app = FastAPI(title="Creator media delivery logs")


@app.post("/media-jobs", response_model=MediaJobResult)
def create_media_job(job: MediaJobRequest, logs: InfraiLogs = Depends(get_logs)) -> MediaJobResult:
    result = decide_delivery(job)
    try:
        logs.ingest(
            level="info",
            message="creator media job ready for delivery",
            metadata={
                "asset_id": job.asset_id,
                "creator_id": job.creator_id,
                "order_id": job.order_id,
                "source_format": job.source_format,
                "delivery_format": job.delivery_format,
                "state": result.state,
            },
        )
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return result


@app.get("/delivery-logs")
def search_delivery_logs(
    order_id: Annotated[str, Query(min_length=1)],
    logs: InfraiLogs = Depends(get_logs),
) -> dict:
    try:
        return logs.search(order_id)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
