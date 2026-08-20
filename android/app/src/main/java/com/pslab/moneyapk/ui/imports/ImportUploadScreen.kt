package com.pslab.moneyapk.ui.imports

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

/**
 * Не единственно верный набор MIME-типов CSV — разные приложения-источники
 * (Файлы, Google Drive и т.п.) объявляют CSV по-разному. Системный пикер
 * (Storage Access Framework) фильтрует по этому списку, но не запрещает
 * пользователю всё равно выбрать что-то другое — на этот случай бэкенд
 * сам вернёт 422 "формат не распознан" (см. ImportUploadViewModel), а не
 * приложение будет пытаться угадывать заранее.
 */
private val CSV_MIME_TYPES = arrayOf(
    "text/csv",
    "text/comma-separated-values",
    "application/vnd.ms-excel",
    "text/plain"
)

/**
 * Первый экран импорта: выбор файла выписки → загрузка на бэкенд.
 * И успешный разбор, и "формат не распознан" ведут дальше на экран превью
 * (см. MainActivity) — он сам показывает нужное состояние по `status`.
 *
 * Кнопка "Назад" в шапке — раньше её не было, и если загрузка виснет
 * (например, бэкенд не отвечает) или пользователь просто передумал —
 * выйти можно было только системным жестом "назад", что не всегда
 * очевидно. Теперь есть явный, видимый способ выйти в любой момент.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ImportUploadScreen(
    onBack: () -> Unit,
    onUploaded: (sessionId: String) -> Unit,
    viewModel: ImportUploadViewModel = viewModel()
) {
    val uiState = viewModel.uiState

    val pickFile = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        uri?.let { viewModel.upload(it) }
    }

    LaunchedEffect(uiState) {
        val state = uiState
        if (state is ImportUploadUiState.Done) {
            onUploaded(state.sessionId)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Импорт выписки") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("Назад")
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "Выбери CSV-файл банковской выписки — бэкенд сам определит банк " +
                    "и разберёт траты.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(bottom = 24.dp)
            )

            if (uiState is ImportUploadUiState.Uploading) {
                CircularProgressIndicator(modifier = Modifier.padding(bottom = 16.dp))
                Text("Загружаем и разбираем файл…")
            } else {
                Button(onClick = { pickFile.launch(CSV_MIME_TYPES) }) {
                    Text("Выбрать файл")
                }
            }

            if (uiState is ImportUploadUiState.Error) {
                Text(
                    text = uiState.message,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 16.dp)
                )
            }
        }
    }
}
