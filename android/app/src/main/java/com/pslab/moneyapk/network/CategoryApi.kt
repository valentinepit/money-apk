package com.pslab.moneyapk.network

import retrofit2.Response
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Field
import retrofit2.http.GET
import retrofit2.http.POST

interface CategoryApi {
    /** По умолчанию бэкенд не возвращает удалённые (soft-deleted) категории. */
    @GET("api/v1/categories")
    suspend fun listCategories(): Response<CategoryListResponse>

    /**
     * Соблюдено правило проекта "POST — через Form" (см. claude/plan.md):
     * тело уходит как application/x-www-form-urlencoded, а не JSON.
     * icon/color на этом шаге не заполняются (см. CategoryListScreen) —
     * backend их поддерживает, но UI пока даёт только название.
     */
    @FormUrlEncoded
    @POST("api/v1/categories")
    suspend fun createCategory(@Field("name") name: String): Response<CategoryDataResponse>
}
