package com.pslab.moneyapk.network

import com.google.gson.annotations.SerializedName

/** Одна транзакция — повторяет `TransactionOut` бэкенда. */
data class TransactionOut(
    val id: String,
    @SerializedName("category_id") val categoryId: String,
    val amount: Double,
    val currency: String,
    @SerializedName("merchant_raw") val merchantRaw: String,
    @SerializedName("merchant_normalized") val merchantNormalized: String,
    val note: String?,
    @SerializedName("transaction_date") val transactionDate: String,
    val source: String,
    @SerializedName("import_session_id") val importSessionId: String?
)

data class PaginationMeta(
    val total: Int,
    val page: Int,
    @SerializedName("per_page") val perPage: Int,
    @SerializedName("total_pages") val totalPages: Int
)

/** Конверт списка транзакций: `GET /api/v1/transactions` -> `{"data": [...], "meta": {...}}`. */
data class TransactionListResponse(
    val data: List<TransactionOut>,
    val meta: PaginationMeta
)

/** Конверт одной транзакции (ответ на создание): `{"data": {...}}`. */
data class TransactionDataResponse(
    val data: TransactionOut
)
