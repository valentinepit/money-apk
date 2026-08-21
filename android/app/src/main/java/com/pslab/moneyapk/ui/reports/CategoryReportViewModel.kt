package com.pslab.moneyapk.ui.reports

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pslab.moneyapk.network.ReportListResponse
import com.pslab.moneyapk.network.RetrofitClient
import kotlinx.coroutines.launch
import java.io.IOException
import java.time.LocalDate
import java.time.format.DateTimeFormatter

sealed interface CategoryReportUiState {
    data object Loading : CategoryReportUiState
    data class Error(val message: String) : CategoryReportUiState
    data class Loaded(val report: ReportListResponse) : CategoryReportUiState
}

/**
 * Отчёт "траты по категориям за период" — GET /api/v1/reports/by-category
 * (шаг 4 фазы 4). По умолчанию период — с начала текущего месяца по сегодня,
 * пользователь может поменять обе границы через DatePicker на экране.
 */
class CategoryReportViewModel(application: Application) : AndroidViewModel(application) {

    private val isoFormatter = DateTimeFormatter.ISO_LOCAL_DATE

    // "private set" у var-свойства с делегатом mutableStateOf заставляет Kotlin
    // сгенерировать в байткоде JVM-метод setDateFrom(String)/setDateTo(String)
    // (обычное java-style имя сеттера для свойства dateFrom/dateTo) — поэтому
    // ниже методы для изменения этих значений называются иначе
    // (onDateFromChanged/onDateToChanged), а не setDateFrom/setDateTo: два
    // метода с одинаковым именем и параметрами на JVM конфликтуют
    // ("Platform declaration clash"), даже если Kotlin не считает это дублем.
    var dateFrom by mutableStateOf(LocalDate.now().withDayOfMonth(1).format(isoFormatter))
        private set
    var dateTo by mutableStateOf(LocalDate.now().format(isoFormatter))
        private set

    var uiState by mutableStateOf<CategoryReportUiState>(CategoryReportUiState.Loading)
        private set

    init {
        load()
    }

    fun onDateFromChanged(value: String) {
        dateFrom = value
        load()
    }

    fun onDateToChanged(value: String) {
        dateTo = value
        load()
    }

    fun load() {
        uiState = CategoryReportUiState.Loading
        viewModelScope.launch {
            try {
                val response = RetrofitClient.reportApi.getByCategory(dateFrom, dateTo)
                uiState = if (response.isSuccessful && response.body() != null) {
                    CategoryReportUiState.Loaded(response.body()!!)
                } else {
                    CategoryReportUiState.Error("Сервер вернул ошибку (код ${response.code()})")
                }
            } catch (e: IOException) {
                uiState = CategoryReportUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                uiState = CategoryReportUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }
}
