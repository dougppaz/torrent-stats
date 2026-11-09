from __future__ import annotations

import logging
from typing import Annotated, TypeAlias

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from torrent_stats.api.depends import (
    TaskRepositoryDepends,
    TorrentRepositoryDepends,
    WorkerKeyRepositoryDepends,
)
from torrent_stats.api.schemas import ActionSuccessResponse, TaskClaimResponse
from torrent_stats.controllers.worker import (
    TaskClaimController,
    TorrentUploadController,
    TrackerStatsController,
)
from torrent_stats.services.storage import storage_manager
from torrent_stats.settings import worker_settings

router = APIRouter(prefix="/worker", tags=["worker"])
logger = logging.getLogger("torrent_stats.worker")


def verify_worker_key(
    worker_key_repository: WorkerKeyRepositoryDepends,
    x_worker_key: Annotated[str | None, Header(alias="X-Worker-Key")] = None,
) -> str:
    if not x_worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Key header",
        )
    if worker_settings.worker_allow_any_key:
        return x_worker_key
    worker_key = worker_key_repository.find_by_key_hash(x_worker_key)
    if not worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Worker-Key",
        )
    return x_worker_key


def get_task_claim_controller(
    task_repository: TaskRepositoryDepends,
) -> TaskClaimController:
    return TaskClaimController(
        task_repository=task_repository,
        worker_settings=worker_settings,
    )


def get_torrent_upload_controller(
    torrent_repository: TorrentRepositoryDepends,
    task_repository: TaskRepositoryDepends,
) -> TorrentUploadController:
    return TorrentUploadController(
        torrent_repository=torrent_repository,
        task_repository=task_repository,
        storage_manager=storage_manager,
    )


def get_tracker_stats_controller(
    torrent_repository: TorrentRepositoryDepends,
    task_repository: TaskRepositoryDepends,
) -> TrackerStatsController:
    return TrackerStatsController(
        torrent_repository=torrent_repository,
        task_repository=task_repository,
    )


TaskClaimControllerDepends: TypeAlias = Annotated[
    TaskClaimController, Depends(get_task_claim_controller)
]
TorrentUploadControllerDepends: TypeAlias = Annotated[
    TorrentUploadController, Depends(get_torrent_upload_controller)
]
TrackerStatsControllerDepends: TypeAlias = Annotated[
    TrackerStatsController, Depends(get_tracker_stats_controller)
]


@router.post(
    "/tasks/claim",
    status_code=status.HTTP_200_OK,
    response_model=TaskClaimResponse | None,
)
def claim_task(
    response: Response,
    controller: TaskClaimControllerDepends,
    _: str = Depends(verify_worker_key),
):
    res = controller.claim_task()
    if res is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return res


@router.post(
    "/torrents",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionSuccessResponse,
)
async def upload_torrent(
    info_hash: Annotated[str, Form()],
    name: Annotated[str, Form()],
    total_size: Annotated[int, Form()],
    controller: TorrentUploadControllerDepends,
    torrent_file: UploadFile = File(...),  # noqa: B008
    storage_profile_key: Annotated[str | None, Form()] = None,
    storage_params: Annotated[str | None, Form()] = None,
    files: Annotated[str | None, Form()] = None,
    _: str = Depends(verify_worker_key),
):
    return await controller.upload_torrent(
        info_hash=info_hash,
        name=name,
        total_size=total_size,
        torrent_file=torrent_file,
        storage_profile_key=storage_profile_key,
        storage_params=storage_params,
        files=files,
    )


class TrackerStatsSubmit(BaseModel):
    tracker_url: str
    success: bool
    seeds: int | None = 0
    peers: int | None = 0


@router.post(
    "/torrents/{hash}/stats",
    status_code=status.HTTP_200_OK,
    response_model=ActionSuccessResponse,
)
def submit_tracker_stats(
    hash: str,
    payload: TrackerStatsSubmit,
    controller: TrackerStatsControllerDepends,
    _: str = Depends(verify_worker_key),
):
    return controller.submit_stats(
        hash=hash,
        tracker_url=payload.tracker_url,
        success=payload.success,
        seeds=payload.seeds,
        peers=payload.peers,
    )
