package com.pslab.moneyapk

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.pslab.moneyapk.data.TokenStore
import com.pslab.moneyapk.ui.categories.CategoryListScreen
import com.pslab.moneyapk.ui.imports.ImportPreviewScreen
import com.pslab.moneyapk.ui.imports.ImportUploadScreen
import com.pslab.moneyapk.ui.login.LoginScreen
import com.pslab.moneyapk.ui.reports.CategoryReportScreen
import com.pslab.moneyapk.ui.theme.MoneyApkTheme
import com.pslab.moneyapk.ui.transactions.ManualEntryScreen
import com.pslab.moneyapk.ui.transactions.TransactionListScreen

/**
 * Шаг 3 фазы 4: список транзакций + ручной ввод. Шаг 4: отчёт по категориям.
 * Фаза 5: импорт выписки (загрузка файла → превью → подтверждение).
 *
 * Экранов стало больше двух, поэтому вместо ручного if/else (как было в
 * шаге 2 для логин/приветствие) используется Navigation Compose — `NavHost`
 * описывает все возможные экраны-маршруты ([Routes]), `NavController`
 * переключает между ними и хранит стек (чтобы, например, кнопка "назад"
 * с экрана ручного ввода естественно возвращала к списку транзакций).
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
                    val navController = rememberNavController()

                    // Простая проверка "уже вошли или нет" — при запуске
                    // приложения читаем сохранённый токен и решаем, с какого
                    // экрана начать: сразу со списка транзакций или с логина.
                    val startDestination = if (tokenStore.getToken() != null) {
                        Routes.TRANSACTIONS
                    } else {
                        Routes.LOGIN
                    }

                    NavHost(navController = navController, startDestination = startDestination) {
                        composable(Routes.LOGIN) {
                            LoginScreen(
                                onLoginSuccess = {
                                    navController.navigate(Routes.TRANSACTIONS) {
                                        // Экран логина убираем из стека — кнопка
                                        // "назад" со списка транзакций не должна
                                        // возвращать на уже пройденный логин.
                                        popUpTo(Routes.LOGIN) { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable(Routes.TRANSACTIONS) {
                            TransactionListScreen(
                                onAddTransaction = { navController.navigate(Routes.ADD_TRANSACTION) },
                                onOpenReport = { navController.navigate(Routes.CATEGORY_REPORT) },
                                onOpenCategories = { navController.navigate(Routes.CATEGORIES) },
                                onOpenImport = { navController.navigate(Routes.IMPORT_UPLOAD) },
                                onLogout = {
                                    tokenStore.clearToken()
                                    navController.navigate(Routes.LOGIN) {
                                        popUpTo(0) { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable(Routes.ADD_TRANSACTION) {
                            ManualEntryScreen(
                                onDone = { navController.popBackStack() }
                            )
                        }
                        composable(Routes.CATEGORY_REPORT) {
                            CategoryReportScreen(
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable(Routes.CATEGORIES) {
                            CategoryListScreen(
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable(Routes.IMPORT_UPLOAD) {
                            ImportUploadScreen(
                                onBack = { navController.popBackStack() },
                                onUploaded = { sessionId ->
                                    navController.navigate(Routes.importPreview(sessionId)) {
                                        // Экран выбора файла убираем из стека — после загрузки
                                        // кнопка "назад" с превью должна вести к списку транзакций,
                                        // а не обратно на пустой экран выбора файла.
                                        popUpTo(Routes.IMPORT_UPLOAD) { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable(
                            route = Routes.IMPORT_PREVIEW,
                            arguments = listOf(navArgument("sessionId") { type = NavType.StringType })
                        ) { backStackEntry ->
                            val sessionId = backStackEntry.arguments?.getString("sessionId")
                            if (sessionId != null) {
                                ImportPreviewScreen(
                                    sessionId = sessionId,
                                    onBack = { navController.popBackStack() },
                                    onDone = {
                                        // Подтверждение импорта создало транзакции — возвращаемся
                                        // сразу к списку, а не по одному экрану назад через превью.
                                        navController.popBackStack(Routes.TRANSACTIONS, inclusive = false)
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private object Routes {
    const val LOGIN = "login"
    const val TRANSACTIONS = "transactions"
    const val ADD_TRANSACTION = "addTransaction"
    const val CATEGORY_REPORT = "categoryReport"
    const val CATEGORIES = "categories"
    const val IMPORT_UPLOAD = "importUpload"
    const val IMPORT_PREVIEW = "importPreview/{sessionId}"

    fun importPreview(sessionId: String) = "importPreview/$sessionId"
}
