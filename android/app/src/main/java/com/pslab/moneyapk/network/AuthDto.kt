package com.pslab.moneyapk.network

import com.google.gson.annotations.SerializedName

/**
 * DTO = Data Transfer Object — классы, форма которых один в один повторяет
 * JSON, который отдаёт бэкенд. Их единственная задача — донести данные с
 * сервера до кода приложения; они не содержат логики.
 *
 * Конверт ответа у бэкенда всегда `{"data": ...}` (успех) или
 * `{"error": {...}}` (ошибка) — см. docs/api/api-contract.md, раздел
 * "Общие конвенции". [ApiEnvelope] — обёртка под успешный ответ, дженерик
 * (годится для любого будущего эндпоинта, не только логина).
 */
data class ApiEnvelope<T>(
    val data: T
)

/** Тело успешного ответа POST /api/v1/auth/login. */
data class LoginData(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

/** Конверт ошибки бэкенда: `{"error": {"code", "message", "details"}}`. */
data class ApiErrorEnvelope(
    val error: ApiErrorBody
)

data class ApiErrorBody(
    val code: String,
    val message: String,
    val details: List<Map<String, Any?>>? = null
)
