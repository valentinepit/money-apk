package com.pslab.moneyapk.network

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Query

interface ReportApi {
    /**
     * [dateFrom]/[dateTo] — строки формата "YYYY-MM-DD" (обязательные query-параметры
     * на бэкенде, см. GET /api/v1/reports/by-category).
     */
    @GET("api/v1/reports/by-category")
    suspend fun getByCategory(
        @Query("date_from") dateFrom: String,
        @Query("date_to") dateTo: String
    ): Response<ReportListResponse>
}
