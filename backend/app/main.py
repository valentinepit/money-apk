from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.errors import APIError, api_error_handler, validation_error_handler
from app.routers import auth, categories, categorization_rules, reports, transactions

app = FastAPI(title="Money apk API", version="0.1.0")

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(categorization_rules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
