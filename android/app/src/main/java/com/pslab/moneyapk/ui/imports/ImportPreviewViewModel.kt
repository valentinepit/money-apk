package com.pslab.moneyapk.ui.imports

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.pslab.moneyapk.network.ApiErrorEnvelope
import com.pslab.moneyapk.network.CategoryOut
import com.pslab.moneyapk.network.ImportSessionConfirmLine
import com.pslab.moneyapk.network.ImportSessionConfirmRequest
import com.pslab.moneyapk.network.ImportSessionDetailData
import com.pslab.moneyapk.network.ImportSessionDetailResponse
import com.pslab.moneyapk.network.RetrofitClient
import kotlinx.coroutines.launch
import retrofit2.Response
import java.io.IOException

sealed interface ImportPreviewUiState {
    data object Loading : ImportPreviewUiState
    data class Error(val message: String) : ImportPreviewUiState
    data class Loaded(val detail: ImportSessionDetailData) : ImportPreviewUiState
}

sealed interface ImportConfirmUiState {
    data object Idle : ImportConfirmUiState
    data object Confirming : ImportConfirmUiState
    data class Error(val message: String) : ImportConfirmUiState
    data object Done : ImportConfirmUiState
}

/**
 * Правки пользователя по каждой строке превью хранятся тут же (в компоуз-
 * состояниях ViewModel), не во View — при повороте экрана/рекомпозиции они
 * не теряются. Изначально категория каждой строки — предложенная бэкендом
 * (`suggested_category_id`), пользователь может её сменить или исключить
 * строку целиком; ничего из этого не отправляется на сервер до нажатия
 * "Подтвердить".
 */
class ImportPreviewViewModel(application: Application) : AndroidViewModel(application) {

    private val gson = Gson()

    var uiState by mutableStateOf<ImportPreviewUiState>(ImportPreviewUiState.Loading)
        private set
    var confirmState by mutableStateOf<ImportConfirmUiState>(ImportConfirmUiState.Idle)
        private set
    var categories by mutableStateOf<List<CategoryOut>>(emptyList())
        private set

    // Отдельное состояние для диалога "Новая категория" — по той же причине,
    // что и в CategoryListViewModel: ошибка сохранения не должна перекрывать
    // уже загруженный список строк превью.
    var isSavingCategory by mutableStateOf(false)
        private set
    var categorySaveError by mutableStateOf<String?>(null)
        private set

    private val categoryByLine = mutableStateMapOf<Int, String>()
    private val excludedLines = mutableStateMapOf<Int, Boolean>()

    fun load(sessionId: String) {
        uiState = ImportPreviewUiState.Loading
        confirmState = ImportConfirmUiState.Idle
        viewModelScope.launch {
            try {
                val categoriesResponse = RetrofitClient.categoryApi.listCategories()
                categories = if (categoriesResponse.isSuccessful) {
                    categoriesResponse.body()?.data.orEmpty()
                } else {
                    emptyList()
                }

                val response = RetrofitClient.importSessionApi.getImportSession(sessionId)
                val body = parseDetailBody(response)
                if (body != null) {
                    categoryByLine.clear()
                    excludedLines.clear()
                    body.data.preview.forEach { row -> categoryByLine[row.lineNo] = row.suggestedCategoryId }
                    uiState = ImportPreviewUiState.Loaded(body.data)
                } else {
                    uiState = ImportPreviewUiState.Error("Не удалось загрузить импорт-сессию (код ${response.code()})")
                }
            } catch (e: IOException) {
                uiState = ImportPreviewUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                uiState = ImportPreviewUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }

    fun categoryIdFor(lineNo: Int): String? = categoryByLine[lineNo]

    fun isExcluded(lineNo: Int): Boolean = excludedLines[lineNo] == true

    fun setCategory(lineNo: Int, categoryId: String) {
        categoryByLine[lineNo] = categoryId
    }

    fun setExcluded(lineNo: Int, excluded: Boolean) {
        excludedLines[lineNo] = excluded
    }

    /**
     * Создаёт новую категорию прямо из превью импорта (когда среди уже
     * существующих нет подходящей) и сразу назначает её строке [forLineNo].
     * Список категорий перезагружается целиком, чтобы новая категория стала
     * видна и в выпадающих списках остальных строк.
     */
    fun createCategory(name: String, forLineNo: Int, onDone: () -> Unit) {
        val trimmed = name.trim()
        if (trimmed.isEmpty()) {
            categorySaveError = "Введите название категории."
            return
        }
        isSavingCategory = true
        categorySaveError = null
        viewModelScope.launch {
            try {
                val response = RetrofitClient.categoryApi.createCategory(trimmed)
                val created = response.body()?.data
                if (response.isSuccessful && created != null) {
                    val categoriesResponse = RetrofitClient.categoryApi.listCategories()
                    categories = if (categoriesResponse.isSuccessful) {
                        categoriesResponse.body()?.data.orEmpty()
                    } else {
                        categories + created
                    }
                    categoryByLine[forLineNo] = created.id
                    isSavingCategory = false
                    onDone()
                } else {
                    isSavingCategory = false
                    categorySaveError = "Сервер вернул ошибку (код ${response.code()})"
                }
            } catch (e: IOException) {
                isSavingCategory = false
                categorySaveError = "Не удалось связаться с сервером."
            } catch (e: Exception) {
                isSavingCategory = false
                categorySaveError = "Непредвиденная ошибка: ${e.message}"
            }
        }
    }

    fun clearCategorySaveError() {
        categorySaveError = null
    }

    fun confirm(sessionId: String, onDone: () -> Unit) {
        val state = uiState
        if (state !is ImportPreviewUiState.Loaded) return

        confirmState = ImportConfirmUiState.Confirming
        viewModelScope.launch {
            try {
                val lines = state.detail.preview.map { row ->
                    ImportSessionConfirmLine(
                        lineNo = row.lineNo,
                        categoryId = categoryByLine[row.lineNo],
                        exclude = excludedLines[row.lineNo] == true
                    )
                }
                val response = RetrofitClient.importSessionApi.confirmImportSession(
                    sessionId,
                    ImportSessionConfirmRequest(lines)
                )
                if (response.isSuccessful) {
                    confirmState = ImportConfirmUiState.Done
                    onDone()
                } else {
                    confirmState = ImportConfirmUiState.Error(parseErrorMessage(response.errorBody()?.string()))
                }
            } catch (e: IOException) {
                confirmState = ImportConfirmUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                confirmState = ImportConfirmUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }

    private fun parseDetailBody(response: Response<ImportSessionDetailResponse>): ImportSessionDetailResponse? {
        response.body()?.let { return it }
        val raw = response.errorBody()?.string() ?: return null
        return try {
            RetrofitClient.gson.fromJson(raw, ImportSessionDetailResponse::class.java)
        } catch (e: Exception) {
            null
        }
    }

    private fun parseErrorMessage(rawBody: String?): String {
        if (rawBody.isNullOrBlank()) return "Сервер вернул ошибку без описания"
        return try {
            gson.fromJson(rawBody, ApiErrorEnvelope::class.java).error.message
        } catch (e: Exception) {
            "Ошибка сервера: $rawBody"
        }
    }
}
