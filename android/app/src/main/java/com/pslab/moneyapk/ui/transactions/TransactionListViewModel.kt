package com.pslab.moneyapk.ui.transactions

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pslab.moneyapk.network.CategoryOut
import com.pslab.moneyapk.network.RetrofitClient
import com.pslab.moneyapk.network.TransactionOut
import kotlinx.coroutines.launch
import java.io.IOException

sealed interface TransactionListUiState {
    data object Loading : TransactionListUiState
    data class Error(val message: String) : TransactionListUiState
    data class Loaded(
        val transactions: List<TransactionOut>,
        val categoriesById: Map<String, CategoryOut>
    ) : TransactionListUiState
}

/**
 * Загружает категории (чтобы показать название, а не id) и первую страницу
 * транзакций. Пагинация (переход на вторую и следующие страницы) в этой
 * версии не реализована — только первая страница (по умолчанию 50 штук),
 * этого достаточно для проверки цикла "добавил → увидел в списке".
 */
class TransactionListViewModel(application: Application) : AndroidViewModel(application) {

    var uiState by mutableStateOf<TransactionListUiState>(TransactionListUiState.Loading)
        private set

    init {
        load()
    }

    fun load() {
        uiState = TransactionListUiState.Loading
        viewModelScope.launch {
            try {
                val categoriesResponse = RetrofitClient.categoryApi.listCategories()
                val categoriesById = if (categoriesResponse.isSuccessful) {
                    categoriesResponse.body()?.data.orEmpty().associateBy { it.id }
                } else {
                    emptyMap()
                }

                val transactionsResponse = RetrofitClient.transactionApi.listTransactions()
                if (transactionsResponse.isSuccessful) {
                    val transactions = transactionsResponse.body()?.data.orEmpty()
                    uiState = TransactionListUiState.Loaded(transactions, categoriesById)
                } else {
                    uiState = TransactionListUiState.Error("Не удалось загрузить транзакции")
                }
            } catch (e: IOException) {
                uiState = TransactionListUiState.Error(
                    "Не удалось связаться с сервером. Проверь, что бэкенд запущен."
                )
            } catch (e: Exception) {
                uiState = TransactionListUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }
}
