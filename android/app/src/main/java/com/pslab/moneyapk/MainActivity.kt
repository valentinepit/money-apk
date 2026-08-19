package com.pslab.moneyapk

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.pslab.moneyapk.data.TokenStore
import com.pslab.moneyapk.ui.login.LoginScreen
import com.pslab.moneyapk.ui.theme.MoneyApkTheme

/**
 * Шаг 2 фазы 4: экран логина + сетевой слой.
 *
 * Пока в приложении только один "настоящий" экран после входа — тот же
 * WelcomeScreen из шага 1, только с добавленной кнопкой "Выйти" для удобства
 * тестирования. Реальные экраны (отчёты, транзакции, ручной ввод) появятся
 * на следующих шагах.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MoneyApkTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val context = LocalContext.current
                    val tokenStore = remember { TokenStore(context) }

                    // Простая проверка "уже вошли или нет" — при запуске
                    // приложения читаем сохранённый токен. Если он есть,
                    // сразу показываем WelcomeScreen, минуя логин.
                    var isLoggedIn by remember { mutableStateOf(tokenStore.getToken() != null) }

                    if (isLoggedIn) {
                        WelcomeScreen(
                            onLogout = {
                                tokenStore.clearToken()
                                isLoggedIn = false
                            }
                        )
                    } else {
                        LoginScreen(onLoginSuccess = { isLoggedIn = true })
                    }
                }
            }
        }
    }
}

@Composable
fun WelcomeScreen(onLogout: () -> Unit = {}) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Money apk",
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Вход выполнен. Следующий шаг — реальные экраны " +
                "(отчёты, транзакции, ручной ввод).",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 12.dp)
        )
        Button(
            onClick = onLogout,
            modifier = Modifier.padding(top = 20.dp)
        ) {
            Text("Выйти")
        }
    }
}

@Preview(showBackground = true)
@Composable
fun WelcomeScreenPreview() {
    MoneyApkTheme {
        WelcomeScreen()
    }
}
