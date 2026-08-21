package com.pslab.moneyapk.ui.imports

import android.app.Application
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pslab.moneyapk.network.ImportSessionDetailResponse
import com.pslab.moneyapk.network.RetrofitClient
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Response
import java.io.IOException

sealed interface ImportUploadUiState {
    data object Idle : ImportUploadUiState
    data object Uploading : ImportUploadUiState
    data class Error(val message: String) : ImportUploadUiState
    /** Успех и "формат не распознан" (422) — оба ведут на экран превью, он сам решит, что показать. */
    data class Done(val sessionId: String) : ImportUploadUiState
}

class ImportUploadViewModel(application: Application) : AndroidViewModel(application) {

    var uiState by mutableStateOf<ImportUploadUiState>(ImportUploadUiState.Idle)
        private set

    fun upload(uri: Uri) {
        uiState = ImportUploadUiState.Uploading
        viewModelScope.launch {
            try {
                val context = getApplication<Application>()
                val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                if (bytes == null) {
                    uiState = ImportUploadUiState.Error("Не удалось прочитать выбранный файл")
                    return@launch
                }
                val fileName = queryFileName(context, uri) ?: "statement.csv"
                val requestBody = bytes.toRequestBody("text/csv".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", fileName, requestBody)

                val response = RetrofitClient.importSessionApi.createImportSession(part)
                val body = parseDetailBody(response)
                uiState = if (body != null) {
                    ImportUploadUiState.Done(body.data.importSession.id)
                } else {
                    ImportUploadUiState.Error("Сервер вернул ошибку (код ${response.code()})")
                }
            } catch (e: IOException) {
                uiState = ImportUploadUiState.Error("Не удалось связаться с сервером.")
            } catch (e: Exception) {
                uiState = ImportUploadUiState.Error("Непредвиденная ошибка: ${e.message}")
            }
        }
    }

    /**
     * Файлы, выбранные через системный пикер (Storage Access Framework),
     * приходят как `content://` URI без читаемого имени файла в самом URI —
     * настоящее имя нужно запросить у content-провайдера отдельно.
     */
    private fun queryFileName(context: Context, uri: Uri): String? {
        var name: String? = null
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (nameIndex >= 0 && cursor.moveToFirst()) {
                name = cursor.getString(nameIndex)
            }
        }
        return name
    }

    /**
     * И 201 (успех), и 422 (нераспознанный/битый файл) отдают одинаковое
     * тело [ImportSessionDetailResponse] — но Retrofit кладёт тело
     * неуспешного (422) ответа в `errorBody()`, а не в `body()`, поэтому на
     * этот случай парсим вручную тем же Gson, что использует конвертер.
     */
    private fun parseDetailBody(response: Response<ImportSessionDetailResponse>): ImportSessionDetailResponse? {
        response.body()?.let { return it }
        val raw = response.errorBody()?.string() ?: return null
        return try {
            RetrofitClient.gson.fromJson(raw, ImportSessionDetailResponse::class.java)
        } catch (e: Exception) {
            null
        }
    }
}
