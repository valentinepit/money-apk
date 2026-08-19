package com.pslab.moneyapk.ui.transactions

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.pslab.moneyapk.network.ApiErrorEnvelope
import com.pslab.moneyapk.network.CategoryOut
import com.pslab.moneyapk.network.RetrofitClient
import kotlinx.coroutines.launch
import java.io.IOException

sealed interface ManualEntryUiState {
    data object Idle : ManualEntryUiState
    data object Loading : ManualEntryUiState
    data class Error(val message: String) : ManualEntryUiState
    data object Success : ManualEntryUiState
}

class ManualEntryViewModel(application: Application) : AndroidViewModel(application) {

    private val gson = Gson()

    var uiState by mutableStateOf<ManualEntryUiState>(ManualEntryUiState.Idle)
        private set

    /** Список категорий для выпадающего меню — необязателен для отправки формы. */
    var categories by mutableStateOf<List<CategoryOut>>(emptyList())
        private set

    init {
        loadCategories()
    }

    private fun loadCategories() {
        viewModelScope.launch {
            try {
                val response = RetrofitClient.categoryApi.listCategories()
                if (response.isSuccessful) {
                    categories = response.body()?.data.orEmpty()
                }
            } catch (e: Exception) {
                // Не критично: если список категорий не загрузился, форму всё
                // равно можно отправить — просто без выбора категории.
            }
        }
    }

    /**
     * @param amountText сумма как введена пользователем (может быть с запятой) —
     * парсится здесь, а не во View, чтобы логика валидации жила в одном месте.
     */
    fun submit(
        amountText: String,
        merchant: String,
        note: String,
        transactionDate: String,
        categoryId: String?
    ) {
        val amount = amountText.replace(',', '.').toDoubleOrNull()
        if (amount == null || amount <= 0) {
            uiState = ManualEntryUiState.Error("Сумма должна быть больше нуля")
            return
        }
        if (transactionDate.isBlank()) {
            uiState = ManualEntryUiState.Error("Укажи дату траты")
            return
        }

        uiState = ManualEntryUiState.Loading
        viewModelScope.launch {
            try {
                val response = RetrofitClient.transactionApi.createTransaction(
                    amount = amount,
                    transactionDate = transactionDate,
                    categoryId = categoryId,
                    merchantRaw = merchant.ifBlank { null },
                    note = note.ifBlank { null }
                )
                uiState = if (response.isSuccessful) {
                    ManualEntryUiState.Success
                } else {
                    ManualEntryUiState.Error(parseErrorMessage(response.errorBody()?.string()))
                }
            } catch (e: IOException) {
                uiState = ManualEntryUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                uiState = ManualEntryUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
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
