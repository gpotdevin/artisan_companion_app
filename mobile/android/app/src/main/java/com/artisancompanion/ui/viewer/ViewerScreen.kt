package com.artisancompanion.ui.viewer

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.data.Marker
import com.artisancompanion.data.Phases
import com.artisancompanion.data.ProfileMeta
import com.artisancompanion.data.Repository
import com.artisancompanion.data.RoastProfile
import com.artisancompanion.data.SensorySummary
import com.artisancompanion.ui.theme.BtRed
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.EtBlue
import com.artisancompanion.ui.theme.RorGrey
import kotlinx.coroutines.launch

class ViewerViewModel : ViewModel() {

    var uiState by mutableStateOf(ViewerUiState())
        private set

    fun load(uuid: String) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, error = null)
            runCatching { Repository.getProfile(uuid) }
                .onSuccess { uiState = uiState.copy(loading = false, profile = it) }
                .onFailure { e -> uiState = uiState.copy(loading = false, error = e.message ?: "Error") }
        }
    }
}

data class ViewerUiState(
    val profile: RoastProfile? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ViewerScreen(
    uuid: String,
    onBack: () -> Unit,
    onEditSensory: () -> Unit,
) {
    val viewModel: ViewerViewModel = viewModel()
    val state = viewModel.uiState
    LaunchedEffect(uuid) { viewModel.load(uuid) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.profile?.title ?: "Roast") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = onEditSensory) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit sensory")
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.loading -> Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
            state.error != null -> Box(Modifier.fillMaxSize(), Alignment.Center) { Text(state.error!!) }
            state.profile != null -> {
                val p = state.profile!!
                Column(
                    Modifier
                        .padding(padding)
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState()),
                ) {
                    ProfileChart(p, Modifier
                        .fillMaxWidth()
                        .height(320.dp))

                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        LegendDot(BtRed, "BT")
                        LegendDot(EtBlue, "ET")
                        LegendDot(RorGrey, "RoR /min")
                    }

                    InfoCard(title = "Phases") {
                        PhaseRow(p.phases)
                    }
                    InfoCard(title = "Markers") {
                        MarkerRow(p.markers)
                    }
                    InfoCard(title = "Roast") {
                        MetaRow(p.meta, p)
                    }
                    InfoCard(title = "Sensory") {
                        SensoryRow(p.sensory)
                    }
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier
            .size(12.dp)
            .background(color))
        Text(label, style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
private fun InfoCard(title: String, content: @Composable () -> Unit) {
    Card(Modifier
        .fillMaxWidth()
        .padding(horizontal = 16.dp, vertical = 4.dp)) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, color = Caramel)
            Spacer(Modifier.height(8.dp))
            content()
        }
    }
}

@Composable
private fun PhaseRow(phases: Phases) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text("Drying: ${fmt(phases.drying_s)}   Maillard: ${fmt(phases.maillard_s)}")
        Text("Development: ${fmt(phases.development_s)}   Total: ${fmt(phases.total_s)}")
    }
}

@Composable
private fun MarkerRow(markers: Map<String, Marker>) {
    if (markers.isEmpty()) {
        Text("No markers")
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        markers.toSortedMap().forEach { (name, m) ->
            Text("$name  ${fmt(m.time_s)}  (${m.temp_bt_c?.let { "%.0f C".format(it) } ?: "--"})")
        }
    }
}

@Composable
private fun MetaRow(meta: ProfileMeta, p: RoastProfile) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text("Artisan ${meta.artisan_version ?: "?"}  ${meta.roastertype ?: ""}")
        Text("Ambient ${meta.ambient_temp_c?.let { "%.1f C".format(it) } ?: "--"}  " +
            "Sample ${meta.sampling_interval_s?.let { "%.0f s".format(it) } ?: "--"}")
        Text("Green ${p.green_weight_g?.let { "%.0f g".format(it) } ?: "--"}  " +
            "Roasted ${p.roasted_weight_g?.let { "%.0f g".format(it) } ?: "--"}  " +
            "Drop ${p.drop_bt_c?.let { "%.1f C".format(it) } ?: "--"}")
    }
}

@Composable
private fun SensoryRow(sensory: SensorySummary?) {
    if (sensory == null) {
        Text("Not annotated yet. Tap Edit to add cupping notes.")
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text("Cuppings: ${sensory.n_cuppings}   Best total: ${sensory.best_total?.let { "%.1f".format(it) } ?: "--"}")
        if (sensory.cuppings.isNotEmpty()) {
            sensory.cuppings.forEach { c ->
                Text("  ${c.date}  total ${c.scores.total?.let { "%.1f".format(it) } ?: "--"}  " +
                    c.descriptors.joinToString(", "))
            }
        }
    }
}

private fun fmt(sec: Double?): String {
    if (sec == null) return "--"
    val total = sec.toInt().coerceAtLeast(0)
    return "${total / 60}:${String.format("%02d", total % 60)}"
}
