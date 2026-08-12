import uuid

from app.exceptions import NotFoundError, RuleIsSystemError
from app.models import CategorizationRule, RuleSource
from app.unit_of_work import AbstractUnitOfWork


async def list_rules(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, source: RuleSource | None = None
) -> list[CategorizationRule]:
    return await uow.categorization_rules.list_visible(user_id, source=source)


async def delete_rule(uow: AbstractUnitOfWork, user_id: uuid.UUID, rule_id: uuid.UUID) -> None:
    rule = await uow.categorization_rules.get_visible(rule_id, user_id)
    if rule is None:
        raise NotFoundError("Правило не найдено")
    if rule.source == RuleSource.system_dictionary:
        raise RuleIsSystemError()
    await uow.categorization_rules.delete(rule)
    await uow.commit()
