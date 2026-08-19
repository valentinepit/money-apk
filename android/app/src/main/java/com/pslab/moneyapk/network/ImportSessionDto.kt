package com.pslab.moneyapk.network

import com.google.gson.annotations.SerializedName

/** Одна импорт-сессия — повторяет `ImportSessionOut` бэкенда. */
data class ImportSessionOut(
    val id: String,
    @SerializedName("file_name") val fileName: String,
    @SerializedName("file_type") val fileType: String,
    @SerializedName("bank_parser") val bankParser: String?,
    val status: String,
    @SerializedName("error_message") val errorMessage: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("confirmed_at") val confirmedAt: String?
)

/**
 * Одна строка превью распознанного файла — повторяет `ImportPreviewRowOut`.
 * Валюта не приходит отдельным полем: money-apk считает только в EUR
 * (см. claude/plan.md, "Регион и валюта").
 */
data class ImportPreviewRowOut(
    @SerializedName("line_no") val lineNo: Int,
    @SerializedName("merchant_raw") val merchantRaw: String,
    @SerializedName("merchant_normalized") val merchantNormalized: String,
    val amount: Double,
    @SerializedName("transaction_date") val transactionDate: String,
    @SerializedName("suggested_category_id") val suggestedCategoryId: String,
    @SerializedName("suggested_category_source") val suggestedCategorySource: String
)

data class ImportSessionDetailData(
    @SerializedName("import_session") val importSession: ImportSessionOut,
    val preview: List<ImportPreviewRowOut>
)

/**
 * Конверт POST/GET одной импорт-сессии: `{"data": {"import_session": {...}, "preview": [...]}}`.
 * Используется и для успешного разбора (201), и для нераспознанного/битого
 * файла (422, `import_session.status == "failed"`, `preview == []`) — обе
 * ветки отдают одно и то же тело (см. docs/api/api-contract.md, "Import").
 */
data class ImportSessionDetailResponse(
    val data: ImportSessionDetailData
)

/** Конверт списка: `GET /api/v1/import-sessions` -> `{"data": [...]}`. */
data class ImportSessionListResponse(
    val data: List<ImportSessionOut>
)

data class ImportConfirmData(
    @SerializedName("created_transactions") val createdTransactions: List<TransactionOut>
)

data class ImportConfirmResponse(
    val data: ImportConfirmData
)

/**
 * Тело `POST /api/v1/import-sessions/:id/confirm` — единственный на проекте
 * эндпоинт с JSON-телом (зафиксированное исключение из правила "POST — Form",
 * см. claude/plan.md, "API-конвенции" — вложенный список правок по строкам
 * не выражается плоскими form-полями).
 *
 * `categoryId == null` — оставить предложенную бэкендом категорию
 * (`suggested_category_id`), не создавать личное правило категоризации.
 */
data class ImportSessionConfirmLine(
    @SerializedName("line_no") val lineNo: Int,
    @SerializedName("category_id") val categoryId: String? = null,
    val exclude: Boolean = false
)

data class ImportSessionConfirmRequest(
    val transactions: List<ImportSessionConfirmLine>
)
