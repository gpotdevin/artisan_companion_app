package com.artisancompanion.ui.radar

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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.R
import com.artisancompanion.data.Repository
import com.artisancompanion.ui.editor.RadarChart
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.CaramelBright
import com.artisancompanion.ui.theme.Cream
import com.artisancompanion.ui.theme.CreamDim
import kotlinx.coroutines.launch

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

class RadarEditorViewModel : ViewModel() {

    var uiState by mutableStateOf(RadarEditorUiState())
        private set

    fun load(uuid: String) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, uuid = uuid)
            val record = runCatching { Repository.getSensory(uuid) }.getOrNull()
            val defaultLabels = runCatching { Repository.radarLabels() }.getOrDefault(emptyList())
            val labels = record?.radar?.labels?.ifEmpty { defaultLabels } ?: defaultLabels
            val values = if (record?.radar?.values?.isNotEmpty() == true) {
                record.radar.values
            } else {
                List(labels.size) { 5.0 }
            }
            uiState = uiState.copy(
                loading = false,
                labels = labels,
                values = values,
            )
        }
    }

    fun setValue(index: Int, value: Double) {
        val next = uiState.values.toMutableList()
        if (index in next.indices) next[index] = value
        uiState = uiState.copy(values = next)
    }

    fun save(onSaved: () -> Unit) {
        viewModelScope.launch {
            uiState = uiState.copy(saving = true, error = null)
            runCatching { Repository.updateRadar(uiState.uuid, uiState.values, uiState.labels) }
                .onSuccess {
                    uiState = uiState.copy(saving = false)
                    onSaved()
                }
                .onFailure {
                    uiState = uiState.copy(saving = false, error = it.message)
                }
        }
    }
}

data class RadarEditorUiState(
    val uuid: String = "",
    val labels: List<String> = emptyList(),
    val values: List<Double> = emptyList(),
    val loading: Boolean = true,
    val saving: Boolean = false,
    val error: String? = null,
)

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RadarEditorScreen(
    uuid: String,
    onBack: () -> Unit,
    onSaved: () -> Unit,
) {
    val viewModel: RadarEditorViewModel = viewModel()
    val state = viewModel.uiState
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val radarSavedMessage = stringResource(R.string.msg_radar_saved)

    LaunchedEffect(uuid) { viewModel.load(uuid) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.action_edit_radar)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.common_back))
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize(), Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {

        val configuration = LocalConfiguration.current
        val isWide = configuration.screenWidthDp >= 600

        Column(
            Modifier
                .padding(padding)
                .fillMaxSize(),
        ) {
            if (isWide) {
                Row(Modifier.weight(1f).fillMaxSize()) {
                    Column(
                        Modifier
                            .weight(0.55f)
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        state.labels.forEachIndexed { index, label ->
                            RadarSlider(
                                label = label,
                                value = state.values.getOrNull(index) ?: 0.0,
                                onValueChange = { viewModel.setValue(index, it) },
                            )
                        }
                    }
                    Column(
                        Modifier
                            .weight(0.45f)
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        LiveRadarPreview(labels = state.labels, values = state.values)
                    }
                }
            } else {
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    LiveRadarPreview(labels = state.labels, values = state.values)
                    state.labels.forEachIndexed { index, label ->
                        RadarSlider(
                            label = label,
                            value = state.values.getOrNull(index) ?: 0.0,
                            onValueChange = { viewModel.setValue(index, it) },
                        )
                    }
                }
            }

            // Error
            state.error?.let { err ->
                Text(
                    err,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(horizontal = 16.dp),
                )
            }

            // Save button
            Button(
                onClick = {
                    viewModel.save {
                        scope.launch {
                            snackbarHostState.showSnackbar(radarSavedMessage)
                            onSaved()
                        }
                    }
                },
                enabled = !state.saving && state.labels.isNotEmpty(),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .height(48.dp),
            ) {
                if (state.saving) {
                    CircularProgressIndicator(
                        modifier = Modifier.height(20.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(Icons.Default.Check, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.action_save_radar))
                }
            }
        }
        }
    }
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

@Composable
private fun RadarSlider(
    label: String,
    value: Double,
    onValueChange: (Double) -> Unit,
) {
    Column {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(label, style = MaterialTheme.typography.bodyMedium, color = Cream)
            Text(
                stringResource(R.string.fmt_one_decimal, value),
                style = MaterialTheme.typography.bodyMedium,
                color = CaramelBright,
            )
        }
        Slider(
            value = value.toFloat(),
            onValueChange = { onValueChange(it.toDouble()) },
            valueRange = 0f..10f,
            steps = 19,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            colors = SliderDefaults.colors(
                thumbColor = Caramel,
                activeTrackColor = Caramel,
                inactiveTrackColor = CreamDim.copy(alpha = 0.3f),
            ),
        )
    }
}

@Composable
private fun LiveRadarPreview(
    labels: List<String>,
    values: List<Double>,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                stringResource(R.string.radar_preview_title),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )
            if (labels.isNotEmpty()) {
                RadarChart(
                    labels = labels,
                    values = values,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(260.dp),
                )
            } else {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(120.dp),
                    Alignment.Center,
                ) {
                    Text(
                        stringResource(R.string.radar_loading_labels),
                        style = MaterialTheme.typography.bodySmall,
                        color = CreamDim,
                    )
                }
            }
        }
    }
}
