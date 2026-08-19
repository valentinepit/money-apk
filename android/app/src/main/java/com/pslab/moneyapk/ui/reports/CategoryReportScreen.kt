package com.pslab.moneyapk.ui.reports

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pslab.moneyapk.network.ReportRowOut
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Отчёт "траты по категориям за период" (шаг 4 фазы 4). Диаграмма — обычный
 * pie-chart, нарисованный вручную через Compose Canvas (без сторонней
 * chart-библиотеки — выбор пользователя, см. согласование перед реализацией):
 * каждая категория — один сектор круга, угол пропорционален её доле в общей
 * сумме трат за период.
 */
private val CHART_COLORS = listOf(
    Color(0xFF6750A4),
    Color(0xFF03A9F4),
    Color(0xFFFF9800),
    Color(0xFF4CAF50),
    Color(0xFFE91E63),
    Color(0xFF9C27B0),
    Color(0xFF795548),
    Color(0xFF009688),
    Color(0xFFFFC107),
    Color(0xFF607D8B)
)

private fun colorFor(index: Int): Color = CHART_COLORS[index % CHART_COLORS.size]

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoryReportScreen(
    onBack: () -> Unit,
    viewModel: CategoryReportViewModel = viewModel()
) {
    val uiState = viewModel.uiState
    var editingDateFrom by remember { mutableStateOf(false) }
    var editingDateTo by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Отчёт по категориям") },
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
                .padding(horizontal = 16.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                DateField(label = "С", value = viewModel.dateFrom, onClick = { editingDateFrom = true })
                DateField(label = "По", value = viewModel.dateTo, onClick = { editingDateTo = true })
            }

            Box(modifier = Modifier.fillMaxSize()) {
                when (uiState) {
                    is CategoryReportUiState.Loading -> {
                        CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                    }

                    is CategoryReportUiState.Error -> {
                        Text(
                            text = uiState.message,
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier
                                .align(Alignment.Center)
                                .padding(24.dp)
                        )
                    }

                    is CategoryReportUiState.Loaded -> {
                        val rows = uiState.report.data
                        if (rows.isEmpty()) {
                            Text(
                                text = "За этот период трат не найдено.",
                                modifier = Modifier
                                    .align(Alignment.Center)
                                    .padding(24.dp)
                            )
                        } else {
                            ReportContent(rows = rows, totalOverall = uiState.report.meta.totalOverall)
                        }
                    }
                }
            }
        }
    }

    if (editingDateFrom) {
        DatePickerPopup(
            initialIso = viewModel.dateFrom,
            onDismiss = { editingDateFrom = false },
            onConfirm = { iso ->
                viewModel.onDateFromChanged(iso)
                editingDateFrom = false
            }
        )
    }
    if (editingDateTo) {
        DatePickerPopup(
            initialIso = viewModel.dateTo,
            onDismiss = { editingDateTo = false },
            onConfirm = { iso ->
                viewModel.onDateToChanged(iso)
                editingDateTo = false
            }
        )
    }
}

@Composable
private fun DateField(label: String, value: String, onClick: () -> Unit) {
    Row {
        Text(text = "$label: ", style = MaterialTheme.typography.bodyMedium)
        TextButton(onClick = onClick) {
            Text(value)
        }
    }
}

@Composable
private fun ReportContent(rows: List<ReportRowOut>, totalOverall: Double) {
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            text = String.format(Locale.US, "Всего за период: %.2f EUR", totalOverall),
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp)
        )

        PieChart(
            rows = rows,
            totalOverall = totalOverall,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .padding(bottom = 16.dp)
        )

        LazyColumn(modifier = Modifier.fillMaxSize()) {
            itemsIndexed(rows) { index, row ->
                val percent = if (totalOverall > 0) row.total / totalOverall * 100 else 0.0
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ColorSwatch(color = colorFor(index))
                    Column(modifier = Modifier.padding(start = 12.dp)) {
                        Text(text = row.categoryName, style = MaterialTheme.typography.bodyLarge)
                        Text(
                            text = String.format(
                                Locale.US,
                                "%.2f EUR · %d шт. · %.1f%%",
                                row.total,
                                row.count,
                                percent
                            ),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ColorSwatch(color: Color) {
    Box(
        modifier = Modifier
            .size(16.dp)
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawCircle(color = color)
        }
    }
}

@Composable
private fun PieChart(rows: List<ReportRowOut>, totalOverall: Double, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        if (totalOverall <= 0) return@Canvas
        var startAngle = -90f
        rows.forEachIndexed { index, row ->
            val sweep = (row.total / totalOverall * 360.0).toFloat()
            drawArcSlice(color = colorFor(index), startAngle = startAngle, sweepAngle = sweep)
            startAngle += sweep
        }
    }
}

/**
 * Один сектор круговой диаграммы. Сектор всегда вписан в квадрат, занимающий
 * всю область Canvas (немного отступив от краёв), независимо от формы самого
 * Canvas — так на любом экране получается корректный круг, а не эллипс.
 */
private fun DrawScope.drawArcSlice(color: Color, startAngle: Float, sweepAngle: Float) {
    val diameter = minOf(size.width, size.height)
    val topLeftX = (size.width - diameter) / 2
    val topLeftY = (size.height - diameter) / 2
    drawArc(
        color = color,
        startAngle = startAngle,
        sweepAngle = sweepAngle,
        useCenter = true,
        topLeft = Offset(topLeftX, topLeftY),
        size = Size(diameter, diameter)
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DatePickerPopup(initialIso: String, onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    val datePickerState = rememberDatePickerState(initialSelectedDateMillis = isoToMillis(initialIso))
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = {
                datePickerState.selectedDateMillis?.let { millis ->
                    onConfirm(millisToIso(millis))
                } ?: onDismiss()
            }) {
                Text("Готово")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Отмена")
            }
        }
    ) {
        DatePicker(state = datePickerState)
    }
}

/** [millis] приходит от DatePicker в UTC-полночь выбранного дня — переводим явно в UTC. */
private fun millisToIso(millis: Long): String {
    val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.US)
    formatter.timeZone = TimeZone.getTimeZone("UTC")
    return formatter.format(Date(millis))
}

private fun isoToMillis(iso: String): Long {
    val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.US)
    formatter.timeZone = TimeZone.getTimeZone("UTC")
    return formatter.parse(iso)?.time ?: System.currentTimeMillis()
}
