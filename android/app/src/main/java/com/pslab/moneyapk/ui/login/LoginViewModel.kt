package com.pslab.moneyapk.ui.login

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pslab.moneyapk.data.TokenStore
import com.pslab.moneyapk.network.RetrofitClient
import com.google.gson.Gson
import com.pslab.moneyapk.network.ApiErrorEnvelope
import kotlinx.coroutines.launch
import java.io.IOException

/**
 * Все возможные состояния экрана логина одним sealed-типом — вместо кучи
 * разрозненных булевых флагов (`isLoading`, `hasError`, ...), которые легко
 * привести в противоречивую комбинацию. Compose-экран просто рисует то,
 * что соответствует текущему состоянию.
 */
sealed interface LoginUiState {
    data object Idle : LoginUiState
    data object Loading : LoginUiState
    data class Error(val message: String) : LoginUiState
    data object Success : LoginUiState
}

/**
 * [AndroidViewModel] (а не просто [androidx.lifecycle.ViewModel]) даёт доступ
 * к [Application] — он нужен, чтобы создать [TokenStore] (тому, в свою очередь,
 * нужен Context для доступа к Android Keystore). ViewModel переживает
 * пересоздание экрана (например, поворот телефона), в отличие от обычных
 * переменных в Compose-функции.
 */
class LoginViewModel(application: Application) : AndroidViewModel(application) {

    private val tokenStore = TokenStore(application)
    private val gson = Gson()

    var uiState by mutableStateOf<LoginUiState>(LoginUiState.Idle)
        private set

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            uiState = LoginUiState.Error("Введите email и пароль")
            return
        }

        uiState = LoginUiState.Loading

        // viewModelScope — область видимости корутин, привязанная к жизни
        // ViewModel: если экран закроют посреди запроса, корутина сама
        // отменится, и мы не будем пытаться обновить уже не существующий UI.
        viewModelScope.launch {
            try {
                val response = RetrofitClient.authApi.login(email, password)

                if (response.isSuccessful) {
                    val token = response.body()?.data?.accessToken
                    if (token != null) {
                        tokenStore.saveToken(token)
                        uiState = LoginUiState.Success
                    } else {
                        uiState = LoginUiState.Error("Сервер вернул пустой ответ")
                    }
                } else {
                    uiState = LoginUiState.Error(parseErrorMessage(response.errorBody()?.string()))
                }
            } catch (e: IOException) {
                // Нет соединения: сервер не запущен, неправильный адрес,
                // либо телефон/эмулятор без сети.
                uiState = LoginUiState.Error(
                    "Не удалось связаться с сервером. Проверь, что бэкенд запущен " +
                        "(uvicorn) и телефон/эмулятор видит компьютер."
                )
            } catch (e: Exception) {
                uiState = LoginUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }

    /** Пытается достать читаемое сообщение из конверта ошибки бэкенда, иначе — запасной текст. */
    private fun parseErrorMessage(rawBody: String?): String {
        if (rawBody.isNullOrBlank()) return "Сервер вернул ошибку без описания"
        return try {
            gson.fromJson(rawBody, ApiErrorEnvelope::class.java).error.message
        } catch (e: Exception) {
            "Ошибка сервера: $rawBody"
        }
    }
}
