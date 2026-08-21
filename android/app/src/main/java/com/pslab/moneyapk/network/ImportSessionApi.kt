package com.pslab.moneyapk.network

import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface ImportSessionApi {

    /**
     * Единственный на проекте эндпоинт с файлом — тело `multipart/form-data`,
     * не `application/x-www-form-urlencoded` (правило Form/Query здесь не
     * подходит по смыслу, файл нельзя передать form-полем).
     *
     * Бэкенд возвращает 201 (файл разобран, `status=parsed`) или 422 (формат
     * не распознан/содержимое битое, `status=failed`) — оба случая отдают
     * одинаковое тело [ImportSessionDetailResponse]. Поэтому используем
     * `Response<...>`, а не бросаем исключение на 422 — тело разбирается
     * вручную и в success-, и в error-ветке (см. ImportUploadViewModel).
     */
    @Multipart
    @POST("api/v1/import-sessions")
    suspend fun createImportSession(@Part file: MultipartBody.Part): Response<ImportSessionDetailResponse>

    @GET("api/v1/import-sessions")
    suspend fun listImportSessions(): Response<ImportSessionListResponse>

    @GET("api/v1/import-sessions/{id}")
    suspend fun getImportSession(@Path("id") id: String): Response<ImportSessionDetailResponse>

    /** JSON-тело — зафиксированное исключение из правила Form, см. ImportSessionConfirmRequest. */
    @POST("api/v1/import-sessions/{id}/confirm")
    suspend fun confirmImportSession(
        @Path("id") id: String,
        @Body body: ImportSessionConfirmRequest
    ): Response<ImportConfirmResponse>

    @DELETE("api/v1/import-sessions/{id}")
    suspend fun deleteImportSession(@Path("id") id: String): Response<Unit>
}
