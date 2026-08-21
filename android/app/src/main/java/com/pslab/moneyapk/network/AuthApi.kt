package com.pslab.moneyapk.network

import retrofit2.Response
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

/**
 * Retrofit сам генерирует реализацию этого интерфейса во время выполнения —
 * достаточно описать, как выглядит запрос, а вызов HTTP спрятан внутри.
 *
 * `@FormUrlEncoded` + `@Field` — тело запроса уходит как
 * `application/x-www-form-urlencoded` (email=...&password=...), а не JSON.
 * Это осознанное правило проекта для всех POST/PATCH-эндпоинтов бэкенда
 * (см. docs/api/api-contract.md, "Общие конвенции") — на Android-стороне
 * оно тоже соблюдается.
 *
 * Возвращаем `Response<ApiEnvelope<LoginData>>`, а не просто `ApiEnvelope<LoginData>`,
 * чтобы самим решать, что делать при ошибке (401 и т.п.) — Retrofit не будет
 * бросать исключение на "неуспешный" HTTP-код, а просто пометит response.isSuccessful = false.
 */
interface AuthApi {
    @FormUrlEncoded
    @POST("api/v1/auth/login")
    suspend fun login(
        @Field("email") email: String,
        @Field("password") password: String
    ): Response<ApiEnvelope<LoginData>>
}
