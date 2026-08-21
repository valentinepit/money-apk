import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import JSONResponse

from app.deps import get_current_user, get_uow
from app.errors import conflict, not_found
from app.exceptions import (
    ImportSessionNotConfirmableError,
    NotFoundError,
    SessionAlreadyConfirmedError,
)
from app.models import ImportSession, ImportSessionStatus, User
from app.schemas.requests import ImportSessionConfirmRequest
from app.schemas.responses import (
    ImportConfirmData,
    ImportConfirmResponse,
    ImportPreviewRowOut,
    ImportSessionDetailData,
    ImportSessionDetailResponse,
    ImportSessionListResponse,
    ImportSessionOut,
    TransactionOut,
)
from app.services import import_service
from app.services.import_service import ConfirmLineUpdate
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/import-sessions", tags=["import-sessions"])


def _detail_response(session: ImportSession, status_code: int) -> JSONResponse:
    # Ручная сборка JSONResponse, а не response_model=, — из-за двойного кода
    # ответа (201/422) на POST "" в зависимости от session.status (см.
    # api-contract.md, "Import"): FastAPI применяет response_model только
    # когда роутер возвращает обычный объект, а не готовый Response.
    body = ImportSessionDetailResponse(
        data=ImportSessionDetailData(
            import_session=ImportSessionOut.model_validate(session),
            preview=[ImportPreviewRowOut.model_validate(row) for row in (session.parsed_preview or [])],
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


@router.post("", status_code=201)
async def create_import_session(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> JSONResponse:
    raw_bytes = await file.read()
    session = await import_service.create_import_session(uow, current_user.id, file.filename, raw_bytes)
    status_code = 422 if session.status == ImportSessionStatus.failed else 201
    return _detail_response(session, status_code)


@router.get("", response_model=ImportSessionListResponse)
async def list_import_sessions(
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> ImportSessionListResponse:
    sessions = await import_service.list_import_sessions(uow, current_user.id)
    return ImportSessionListResponse(data=[ImportSessionOut.model_validate(s) for s in sessions])


@router.get("/{session_id}")
async def get_import_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> JSONResponse:
    try:
        session = await import_service.get_import_session(uow, current_user.id, session_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return _detail_response(session, 200)


@router.post("/{session_id}/confirm", response_model=ImportConfirmResponse)
async def confirm_import_session(
    session_id: uuid.UUID,
    payload: ImportSessionConfirmRequest,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> ImportConfirmResponse:
    line_updates = [
        ConfirmLineUpdate(line_no=line.line_no, category_id=line.category_id, exclude=line.exclude)
        for line in payload.transactions
    ]
    try:
        created = await import_service.confirm_import_session(uow, current_user.id, session_id, line_updates)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    except SessionAlreadyConfirmedError as exc:
        raise conflict(exc.code, exc.message) from exc
    except ImportSessionNotConfirmableError as exc:
        raise conflict(exc.code, exc.message) from exc
    return ImportConfirmResponse(
        data=ImportConfirmData(created_transactions=[TransactionOut.model_validate(t) for t in created])
    )


@router.delete("/{session_id}", status_code=204, response_model=None)
async def delete_import_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Response:
    try:
        await import_service.delete_import_session(uow, current_user.id, session_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    except SessionAlreadyConfirmedError as exc:
        raise conflict(exc.code, exc.message) from exc
    return Response(status_code=204)
