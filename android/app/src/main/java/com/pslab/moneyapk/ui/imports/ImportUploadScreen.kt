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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
 */
@Composable
fun ImportUploadScreen(
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

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Импорт выписки",
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Выбери CSV-файл банковской выписки — бэкенд сам определит банк " +
                "и разберёт траты.",
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp)
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
