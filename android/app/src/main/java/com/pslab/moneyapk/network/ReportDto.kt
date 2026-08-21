package com.pslab.moneyapk.network

import com.google.gson.annotations.SerializedName

/**
 * Одна строка отчёта "траты по категориям за период" —
 * см. GET /api/v1/reports/by-category, docs/api/api-contract.md.
 */
data class ReportRowOut(
    @SerializedName("category_id") val categoryId: String,
    @SerializedName("category_name") val categoryName: String,
    val total: Double,
    val count: Int
)

data class ReportMeta(
    @SerializedName("date_from") val dateFrom: String,
    @SerializedName("date_to") val dateTo: String,
    @SerializedName("total_overall") val totalOverall: Double
)

data class ReportListResponse(
    val data: List<ReportRowOut>,
    val meta: ReportMeta
)
