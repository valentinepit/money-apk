package com.pslab.moneyapk.network

import com.google.gson.annotations.SerializedName

/** Одна категория трат — повторяет `CategoryOut` бэкенда. */
data class CategoryOut(
    val id: String,
    val name: String,
    val icon: String?,
    val color: String?,
    @SerializedName("is_system") val isSystem: Boolean
)

/** Конверт списка категорий: `GET /api/v1/categories` -> `{"data": [...]}`. */
data class CategoryListResponse(
    val data: List<CategoryOut>
)
