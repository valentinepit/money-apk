package com.pslab.moneyapk.network

import retrofit2.Response
import retrofit2.http.GET

interface CategoryApi {
    /** По умолчанию бэкенд не возвращает удалённые (soft-deleted) категории. */
    @GET("api/v1/categories")
    suspend fun listCategories(): Response<CategoryListResponse>
}
