"""Доменные исключения сервисного слоя.

Сервисы работают с UnitOfWork/репозиториями и ничего не знают про HTTP —
поэтому они поднимают эти исключения, а не fastapi.HTTPException.
Роутеры (тонкий HTTP-слой) перехватывают их и переводят в app.errors.APIError.
"""


class DomainError(Exception):
    """Базовый класс для всех доменных ошибок."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    def __init__(self, message: str = "Не найдено") -> None:
        super().__init__(message)


class InvalidCredentialsError(DomainError):
    def __init__(self, message: str = "Неверный email или пароль") -> None:
        super().__init__(message)


class UnauthorizedError(DomainError):
    def __init__(self, message: str = "Не авторизован") -> None:
        super().__init__(message)


class ConflictError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CategoryIsSystemError(ConflictError):
    def __init__(self, message: str = "Системную категорию нельзя удалить") -> None:
        super().__init__("category_is_system", message)


class RuleIsSystemError(ConflictError):
    def __init__(self, message: str = "Системное правило нельзя удалить") -> None:
        super().__init__("rule_is_system", message)
