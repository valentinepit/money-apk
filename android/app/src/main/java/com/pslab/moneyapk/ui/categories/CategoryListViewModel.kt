package com.pslab.moneyapk.ui.categories

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pslab.moneyapk.network.CategoryOut
import com.pslab.moneyapk.network.RetrofitClient
import kotlinx.coroutines.launch
import java.io.IOException

sealed interface CategoryListUiState {
    data object Loading : CategoryListUiState
    data class Error(val message: String) : CategoryListUiState
    data class Loaded(val categories: List<CategoryOut>) : CategoryListUiState
}

/**
 * Список категорий + добавление новой (GET/POST /api/v1/categories).
 * На этом шаге форма добавления даёт задать только название — backend
 * поддерживает ещё icon/color, но UI для них пока не сделан.
 */
class CategoryListViewModel(application: Application) : AndroidViewModel(application) {

    var uiState by mutableStateOf<CategoryListUiState>(CategoryListUiState.Loading)
        private set

    // Отдельное состояние для формы добавления — чтобы ошибка сохранения не
    // перекрывала уже загруженный список (в отличие от uiState, который целиком
    // подменяется на Loading/Error при перезагрузке).
    var isSaving by mutableStateOf(false)
        private set
    var saveError by mutableStateOf<String?>(null)
        private set

    init {
        load()
    }

    fun load() {
        uiState = CategoryListUiState.Loading
        viewModelScope.launch {
            try {
                val response = RetrofitClient.categoryApi.listCategories()
                uiState = if (response.isSuccessful && response.body() != null) {
                    CategoryListUiState.Loaded(response.body()!!.data)
                } else {
                    CategoryListUiState.Error("Сервер вернул ошибку (код ${response.code()})")
                }
            } catch (e: IOException) {
                uiState = CategoryListUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                uiState = CategoryListUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }

    fun addCategory(name: String, onDone: () -> Unit) {
        val trimmed = name.trim()
        if (trimmed.isEmpty()) {
            saveError = "Введите название категории."
            return
        }
        isSaving = true
        saveError = null
        viewModelScope.launch {
            try {
                val response = RetrofitClient.categoryApi.createCategory(trimmed)
                if (response.isSuccessful) {
                    isSaving = false
                    onDone()
                    load()
                } else {
                    isSaving = false
                    saveError = "Сервер вернул ошибку (код ${response.code()})"
                }
            } catch (e: IOException) {
                isSaving = false
                saveError = "Не удалось связаться с сервером."
            } catch (e: Exception) {
                isSaving = false
                saveError = "Непредвиденная ошибка: ${e.message}"
            }
        }
    }

    fun clearSaveError() {
        saveError = null
    }
}
