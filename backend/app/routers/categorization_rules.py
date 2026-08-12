import uuid

from fastapi import APIRouter, Depends, Query, Response

from app.deps import get_current_user, get_uow
from app.errors import conflict, not_found
from app.exceptions import NotFoundError, RuleIsSystemError
from app.models import RuleSource, User
from app.schemas.responses import CategorizationRuleListResponse, CategorizationRuleOut
from app.services import categorization_rule_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/categorization-rules", tags=["categorization-rules"])


@router.get("", response_model=CategorizationRuleListResponse)
async def list_rules(
    source: RuleSource | None = Query(None),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> CategorizationRuleListResponse:
    rules = await categorization_rule_service.list_rules(uow, current_user.id, source=source)
    return CategorizationRuleListResponse(data=[CategorizationRuleOut.model_validate(r) for r in rules])


@router.delete("/{rule_id}", status_code=204, response_model=None)
async def delete_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Response:
    try:
        await categorization_rule_service.delete_rule(uow, current_user.id, rule_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    except RuleIsSystemError as exc:
        raise conflict(exc.code, exc.message) from exc
    return Response(status_code=204)
