package com.pslab.moneyapk.ui.imports

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pslab.moneyapk.network.CategoryOut
import com.pslab.moneyapk.network.ImportPreviewRowOut
import java.util.Locale

/**
 * Второй экран импорта: превью распознанных бэкендом строк выписки перед
 * их превращением в настоящие транзакции. Пользователь может по каждой
 * строке сменить предложенную категорию или исключить строку целиком —
 * это ровно то, что поддерживает `POST /api/v1/import-sessions/:id/confirm`
 * (см. docs/api/api-contract.md, "Import").
 *
 * Если бэкенд не смог разобрать файл (`status == "failed"`, 422 при
 * загрузке), вместо списка показывается причина ошибки — экран подтверждения
 * недоступен, только возврат назад.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ImportPreviewScreen(
    sessionId: String,
    onBack: () -> Unit,
    onDone: () -> Unit,
    viewModel: ImportPreviewViewModel = viewModel()
) {
    LaunchedEffect(sessionId) {
        viewModel.load(sessionId)
    }

    val uiState = viewModel.uiState
    val confirmState = viewModel.confirmState

    // Строка, для которой открыт диалог "Новая категория" — null, если диалог
    // закрыт. Живёт здесь (а не во ViewModel), потому что это чисто состояние
    // навигации по UI, не данные, которые нужно переживать смерть процесса.
    var addCategoryForLine by remember { mutableStateOf<Int?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Превью импорта") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("Назад")
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (uiState) {
                is ImportPreviewUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }

                is ImportPreviewUiState.Error -> {
                    Text(
                        text = uiState.message,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(24.dp)
                    )
                }

                is ImportPreviewUiState.Loaded -> {
                    val session = uiState.detail.importSession
                    when (session.status) {
                        "failed" -> FailedContent(errorMessage = session.errorMessage, onBack = onBack)
                        "confirmed" -> AlreadyConfirmedContent(onBack = onBack)
                        else -> PreviewContent(
                            sessionId = sessionId,
                            preview = uiState.detail.preview,
                            categories = viewModel.categories,
                            categoryIdFor = viewModel::categoryIdFor,
                            isExcluded = viewModel::isExcluded,
                            onCategoryChange = viewModel::setCategory,
                            onExcludeChange = viewModel::setExcluded,
                            onRequestNewCategory = { lineNo -> addCategoryForLine = lineNo },
                            confirmState = confirmState,
                            onConfirm = { viewModel.confirm(sessionId, onDone) }
                        )
                    }
                }
            }
        }
    }

    val lineForNewCategory = addCategoryForLine
    if (lineForNewCategory != null) {
        AddCategoryDialog(
            isSaving = viewModel.isSavingCategory,
            errorMessage = viewModel.categorySaveError,
            onDismiss = {
                addCategoryForLine = null
                viewModel.clearCategorySaveError()
            },
            onConfirm = { name ->
                viewModel.createCategory(name, forLineNo = lineForNewCategory) {
                    addCategoryForLine = null
                }
            }
        )
    }
}

@Composable
private fun FailedContent(errorMessage: String?, onBack: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Не удалось разобрать файл",
            style = MaterialTheme.typography.titleLarge
        )
        Text(
            text = errorMessage ?: "Формат файла не распознан.",
            color = MaterialTheme.colorScheme.error,
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp)
        )
        Button(onClick = onBack) {
            Text("Понятно")
        }
    }
}

@Composable
private fun AlreadyConfirmedContent(onBack: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Этот импорт уже подтверждён",
            style = MaterialTheme.typography.titleLarge
        )
        Button(onClick = onBack, modifier = Modifier.padding(top = 24.dp)) {
            Text("Назад")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PreviewContent(
    sessionId: String,
    preview: List<ImportPreviewRowOut>,
    categories: List<CategoryOut>,
    categoryIdFor: (Int) -> String?,
    isExcluded: (Int) -> Boolean,
    onCategoryChange: (Int, String) -> Unit,
    onExcludeChange: (Int, Boolean) -> Unit,
    onRequestNewCategory: (Int) -> Unit,
    confirmState: ImportConfirmUiState,
    onConfirm: () -> Unit
) {
    val categoriesById = remember(categories) { categories.associateBy { it.id } }
    val includedCount = preview.count { !isExcluded(it.lineNo) }

    Column(modifier = Modifier.fillMaxSize()) {
        if (preview.isEmpty()) {
            Text(
                text = "В файле не нашлось расходных операций.",
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(24.dp)
            )
        } else {
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 16.dp)
            ) {
                items(preview, key = { it.lineNo }) { row ->
                    PreviewRow(
                        row = row,
                        categories = categories,
                        categoryName = categoriesById[categoryIdFor(row.lineNo)]?.name ?: "Другое",
                        excluded = isExcluded(row.lineNo),
                        onCategoryChange = { categoryId -> onCategoryChange(row.lineNo, categoryId) },
                        onExcludeChange = { excluded -> onExcludeChange(row.lineNo, excluded) },
                        onRequestNewCategory = { onRequestNewCategory(row.lineNo) }
                    )
                }
            }
        }

        if (confirmState is ImportConfirmUiState.Error) {
            Text(
                text = confirmState.message,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Button(
            onClick = onConfirm,
            enabled = confirmState !is ImportConfirmUiState.Confirming && includedCount > 0,
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            if (confirmState is ImportConfirmUiState.Confirming) {
                CircularProgressIndicator(
                    modifier = Modifier.padding(end = 8.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp
                )
            }
            Text(
                if (confirmState is ImportConfirmUiState.Confirming) {
                    "Подтверждаем…"
                } else {
                    "Подтвердить импорт ($includedCount)"
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PreviewRow(
    row: ImportPreviewRowOut,
    categories: List<CategoryOut>,
    categoryName: String,
    excluded: Boolean,
    onCategoryChange: (String) -> Unit,
    onExcludeChange: (Boolean) -> Unit,
    onRequestNewCategory: () -> Unit
) {
    var categoryExpanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = String.format(Locale.US, "%.2f EUR", row.amount),
                        style = MaterialTheme.typography.titleMedium,
                        textDecoration = if (excluded) TextDecoration.LineThrough else TextDecoration.None
                    )
                    Text(
                        text = row.merchantRaw.ifBlank { "Без названия" },
                        style = MaterialTheme.typography.bodyMedium,
                        textDecoration = if (excluded) TextDecoration.LineThrough else TextDecoration.None
                    )
                    Text(
                        text = row.transactionDate,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Checkbox(checked = excluded, onCheckedChange = onExcludeChange)
                    Text("Исключить", style = MaterialTheme.typography.labelSmall)
                }
            }

            if (!excluded) {
                ExposedDropdownMenuBox(
                    expanded = categoryExpanded,
                    onExpandedChange = { categoryExpanded = it },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    OutlinedTextField(
                        value = categoryName,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Категория") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryExpanded) },
                        modifier = Modifier
                            .menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = categoryExpanded,
                        onDismissRequest = { categoryExpanded = false }
                    ) {
                        // Пункт создания категории — на случай, если среди
                        // существующих нет подходящей прямо во время импорта,
                        // без ухода на отдельный экран "Категории".
                        DropdownMenuItem(
                            text = { Text("+ Новая категория") },
                            onClick = {
                                categoryExpanded = false
                                onRequestNewCategory()
                            }
                        )
                        categories.forEach { category ->
                            DropdownMenuItem(
                                text = { Text(category.name) },
                                onClick = {
                                    onCategoryChange(category.id)
                                    categoryExpanded = false
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AddCategoryDialog(
    isSaving: Boolean,
    errorMessage: String?,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit
) {
    var name by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Новая категория") },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Название") },
                    singleLine = true,
                    enabled = !isSaving,
                    modifier = Modifier.fillMaxWidth()
                )
                if (errorMessage != null) {
                    Text(
                        text = errorMessage,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(name) }, enabled = !isSaving) {
                Text(if (isSaving) "Сохранение..." else "Добавить")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !isSaving) {
                Text("Отмена")
            }
        }
    )
}
