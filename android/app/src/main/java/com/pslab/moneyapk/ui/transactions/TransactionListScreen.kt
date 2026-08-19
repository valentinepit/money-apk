package com.pslab.moneyapk.ui.transactions

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pslab.moneyapk.network.TransactionOut
import java.util.Locale

/**
 * Главный экран после логина (заменяет прежний WelcomeScreen из шага 2).
 * Кнопка "+" (FAB) ведёт на экран ручного ввода, "Выйти" — сбрасывает
 * токен и возвращает на экран логина (навигация — в MainActivity).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionListScreen(
    onAddTransaction: () -> Unit,
    onLogout: () -> Unit,
    viewModel: TransactionListViewModel = viewModel()
) {
    val uiState = viewModel.uiState

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Транзакции") },
                actions = {
                    TextButton(onClick = { viewModel.load() }) {
                        Text("Обновить")
                    }
                    TextButton(onClick = onLogout) {
                        Text("Выйти")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onAddTransaction) {
                Text("+", style = MaterialTheme.typography.headlineMedium)
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (uiState) {
                is TransactionListUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }

                is TransactionListUiState.Error -> {
                    Text(
                        text = uiState.message,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(24.dp)
                    )
                }

                is TransactionListUiState.Loaded -> {
                    if (uiState.transactions.isEmpty()) {
                        Text(
                            text = "Пока нет ни одной транзакции. Нажми \"+\", чтобы добавить первую.",
                            modifier = Modifier
                                .align(Alignment.Center)
                                .padding(24.dp)
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 16.dp)
                        ) {
                            items(uiState.transactions) { transaction ->
                                TransactionRow(
                                    transaction = transaction,
                                    categoryName = uiState.categoriesById[transaction.categoryId]?.name
                                        ?: "Другое"
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TransactionRow(transaction: TransactionOut, categoryName: String) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = String.format(Locale.US, "%.2f %s", transaction.amount, transaction.currency),
                style = MaterialTheme.typography.titleMedium
            )
            Text(
                text = transaction.merchantRaw.ifBlank { "Без названия" },
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                text = "$categoryName · ${transaction.transactionDate}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
