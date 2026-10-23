package com.artisancompanion.ui.editor

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.data.Cupping
import com.artisancompanion.data.Repository
import com.artisancompanion.data.SensoryRecord
import com.artisancompanion.data.SensoryUpdate
import com.artisancompanion.data.Scores
import kotlinx.coroutines.launch

class EditorViewModel : ViewModel() {

    var state by mutableStateOf(EditorUiState())
        private set

    fun load(uuid: String) {
        viewModelScope.launch {
            state = state.copy(loading = true, uuid = uuid)
            val record = runCatching { Repository.getSensory(uuid) }.getOrNull()
            val labels = runCatching { Repository.radarLabels() }.getOrDefault(emptyList())
            val defectKeys = runCatching { Repository.defectKeys() }.getOrDefault(emptyList())
            val scoreKeys = runCatching { Repository.scoreKeys() }.getOrDefault(emptyList())
            state = state.copy(
                loading = false,
                record = record,
                radarLabels = labels,
                radarValues = record?.radar?.values?.ifEmpty { List(labels.size) { 0.0 } }
                    ?: List(labels.size) { 0.0 },
                scoreKeys = scoreKeys,
                defectKeys = defectKeys,
                defects = record?.defects_observed ?: emptyMap(),
            )
        }
    }

    fun setRadarValue(index: Int, value: Double) {
        val next = state.radarValues.toMutableList()
        if (index in next.indices) next[index] = value
        state = state.copy(radarValues = next)
    }

    fun setDefect(key: String, on: Boolean) {
        state = state.copy(defects = state.defects + (key to on))
    }

    fun saveRadar() {
        viewModelScope.launch {
            runCatching { Repository.updateRadar(state.uuid, state.radarValues, state.radarLabels) }
                .onSuccess { rec ->
                    state = state.copy(record = rec, radarValues = rec.radar.values, message = "Radar saved")
                }
                .onFailure { state = state.copy(message = "Error: ${it.message}") }
        }
    }

    fun saveDefects() {
        viewModelScope.launch {
            runCatching { Repository.updateSensory(state.uuid, SensoryUpdate(defects_observed = state.defects)) }
                .onSuccess { rec -> state = state.copy(record = rec, message = "Defects saved") }
                .onFailure { state = state.copy(message = "Error: ${it.message}") }
        }
    }

    fun addCupping(cupping: Cupping) {
        viewModelScope.launch {
            runCatching { Repository.addCupping(state.uuid, cupping) }
                .onSuccess { rec -> state = state.copy(record = rec, message = "Cupping added") }
                .onFailure { state = state.copy(message = "Error: ${it.message}") }
        }
    }

    fun deleteCupping(index: Int) {
        viewModelScope.launch {
            runCatching { Repository.removeCupping(state.uuid, index) }
                .onSuccess { rec -> state = state.copy(record = rec, message = "Cupping removed") }
                .onFailure { state = state.copy(message = "Error: ${it.message}") }
        }
    }
}

data class EditorUiState(
    val uuid: String = "",
    val record: SensoryRecord? = null,
    val radarLabels: List<String> = emptyList(),
    val radarValues: List<Double> = emptyList(),
    val scoreKeys: List<String> = emptyList(),
    val defectKeys: List<String> = emptyList(),
    val defects: Map<String, Boolean> = emptyMap(),
    val loading: Boolean = true,
    val message: String? = null,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditorScreen(uuid: String, onBack: () -> Unit) {
    val viewModel: EditorViewModel = viewModel()
    val state = viewModel.uiState
    LaunchedEffect(uuid) { viewModel.load(uuid) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sensory editor") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.loading -> Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
            else -> Column(
                Modifier
                    .padding(padding)
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                if (state.message != null) {
                    Text(state.message!!, color = MaterialTheme.colorScheme.primary)
                }

                // ---- Radar ----
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Flavor radar", style = MaterialTheme.typography.titleSmall)
                        RadarChart(
                            labels = state.radarLabels,
                            values = state.radarValues,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(220.dp),
                        )
                        state.radarLabels.forEachIndexed { i, label ->
                            Column {
                                Text("$label  ${"%.1f".format(state.radarValues.getOrNull(i) ?: 0.0)}")
                                Slider(
                                    value = (state.radarValues.getOrNull(i) ?: 0.0).toFloat(),
                                    onValueChange = { viewModel.setRadarValue(i, it.toDouble()) },
                                    valueRange = 0f..10f,
                                )
                            }
                        }
                        Button(onClick = { viewModel.saveRadar() }, modifier = Modifier.fillMaxWidth()) {
                            Text("Save radar")
                        }
                    }
                }

                // ---- Defects ----
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Defects observed", style = MaterialTheme.typography.titleSmall)
                        state.defectKeys.forEach { key ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(
                                    checked = state.defects[key] == true,
                                    onCheckedChange = { viewModel.setDefect(key, it) },
                                )
                                Text(key)
                            }
                        }
                        Button(onClick = { viewModel.saveDefects() }, modifier = Modifier.fillMaxWidth()) {
                            Text("Save defects")
                        }
                    }
                }

                // ---- Cuppings ----
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Cupping sessions", style = MaterialTheme.typography.titleSmall)
                        val cuppings = state.record?.cuppings.orEmpty()
                        if (cuppings.isEmpty()) {
                            Text("No cuppings yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        cuppings.forEachIndexed { index, c ->
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text("${c.date}  total ${c.scores.total?.let { "%.1f".format(it) } ?: "--"}")
                                    Text(
                                        c.descriptors.joinToString(", "),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                IconButton(onClick = { viewModel.deleteCupping(index) }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete cupping")
                                }
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                        CuppingForm(
                            scoreKeys = state.scoreKeys,
                            onAdd = { viewModel.addCupping(it) },
                        )
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Cupping form (local UI state)
// ---------------------------------------------------------------------------

private class CuppingFormState {
    var date by mutableStateOf("")
    val scores = mutableStateMapOf<String, String>()
    var descriptors by mutableStateOf("")
    var notes by mutableStateOf("")
}

@Composable
private fun CuppingForm(scoreKeys: List<String>, onAdd: (Cupping) -> Unit) {
    val form = remember { CuppingFormState() }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = form.date,
            onValueChange = { form.date = it },
            label = { Text("Date (YYYY-MM-DD)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        scoreKeys.forEach { key ->
            OutlinedTextField(
                value = form.scores[key].orEmpty(),
                onValueChange = { form.scores[key] = it },
                label = { Text(scoreLabel(key)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        OutlinedTextField(
            value = form.scores["defects"].orEmpty(),
            onValueChange = { form.scores["defects"] = it },
            label = { Text("Defects (penalty)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = form.descriptors,
            onValueChange = { form.descriptors = it },
            label = { Text("Descriptors (comma separated)") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = form.notes,
            onValueChange = { form.notes = it },
            label = { Text("Notes") },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = {
                val cupping = form.toCupping()
                if (cupping != null) {
                    onAdd(cupping)
                    form.date = ""
                    form.scores.clear()
                    form.descriptors = ""
                    form.notes = ""
                }
            },
            enabled = form.date.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text("Add cupping")
        }
    }
}

private fun CuppingFormState.toCupping(): Cupping? {
    if (date.isBlank()) return null
    fun num(key: String): Double? = scores[key]?.toDoubleOrNull()
    val scores = Scores(
        fragrance_aroma = num("fragrance_aroma"),
        flavor = num("flavor"),
        aftertaste = num("aftertaste"),
        acidity = num("acidity"),
        body = num("body"),
        balance = num("balance"),
        uniformity = num("uniformity"),
        clean_cup = num("clean_cup"),
        sweetness = num("sweetness"),
        overall = num("overall"),
        defects = num("defects"),
    )
    val descriptors = descriptors.split(",")
        .map { it.trim() }
        .filter { it.isNotEmpty() }
    return Cupping(
        date = date.trim(),
        scores = scores,
        descriptors = descriptors,
        notes = notes.trim().ifBlank { null },
    )
}

private fun scoreLabel(key: String): String = when (key) {
    "fragrance_aroma" -> "Fragrance / Aroma"
    "flavor" -> "Flavor"
    "aftertaste" -> "Aftertaste"
    "acidity" -> "Acidity"
    "body" -> "Body"
    "balance" -> "Balance"
    "uniformity" -> "Uniformity"
    "clean_cup" -> "Clean Cup"
    "sweetness" -> "Sweetness"
    "overall" -> "Overall"
    else -> key
}
