package com.artisancompanion.ui.viewer

import android.content.res.Configuration
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.R
import com.artisancompanion.data.Repository
import com.artisancompanion.data.RoastEvent
import com.artisancompanion.data.RoastProfile
import com.artisancompanion.ui.sensory.SensoryTab
import com.artisancompanion.ui.theme.BtRed
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.Cream
import com.artisancompanion.ui.theme.CreamDim
import com.artisancompanion.ui.theme.EtBlue
import com.artisancompanion.ui.theme.RorGrey
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.roundToInt

class ViewerViewModel : ViewModel() {

    var uiState by mutableStateOf(ViewerUiState())
        private set

    fun load(uuid: String) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, error = null)
            runCatching { Repository.getProfile(uuid) }
                .onSuccess { uiState = uiState.copy(loading = false, profile = it) }
                .onFailure { e -> uiState = uiState.copy(loading = false, error = e.message) }
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
    onRecordCupping: () -> Unit,
    onEditCupping: (Int) -> Unit,
    onEditRadar: () -> Unit,
) {
    val viewModel: ViewerViewModel = viewModel()
    val state = viewModel.uiState
    LaunchedEffect(uuid) { viewModel.load(uuid) }

    // Curve visibility toggles (default: all shown)
    var showBt by remember { mutableStateOf(true) }
    var showEt by remember { mutableStateOf(true) }
    var showRor by remember { mutableStateOf(true) }

    // Events list expanded / collapsed
    var eventsExpanded by remember { mutableStateOf(false) }

    // Selected tab: 0 = Profile, 1 = Sensory
    var selectedTab by remember { mutableStateOf(0) }

    val configuration = LocalConfiguration.current
    val isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(state.profile?.title ?: stringResource(R.string.viewer_default_title))
                        state.profile?.source_file?.let { file ->
                            Text(
                                file,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.common_back))
                    }
                },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            // -- Tab row --
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = MaterialTheme.colorScheme.surface,
                contentColor = Caramel,
            ) {
                val tabTitles = listOf(
                    stringResource(R.string.tab_profile),
                    stringResource(R.string.tab_sensory),
                )
                tabTitles.forEachIndexed { index, title ->
                    Tab(
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        text = {
                            Text(
                                title,
                                color = if (selectedTab == index) Caramel else CreamDim,
                            )
                        },
                    )
                }
            }

            // -- Tab content --
            when (selectedTab) {
                0 -> {
                    // Profile tab
                    when {
                        state.loading -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                            CircularProgressIndicator()
                        }
                        state.error != null -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                            Text(state.error)
                        }
                        state.profile != null -> {
                            val p = state.profile
                            if (isLandscape) {
                                // Two-pane layout: chart left, info cards right
                                Row(Modifier.fillMaxSize()) {
                                    Column(
                                        Modifier
                                            .weight(0.6f)
                                            .fillMaxSize(),
                                    ) {
                                        ProfileChart(
                                            p,
                                            Modifier
                                                .fillMaxWidth()
                                                .weight(1f),
                                            showBt = showBt,
                                            showEt = showEt,
                                            showRor = showRor,
                                        )
                                        LegendRow(
                                            showBt = showBt,
                                            showEt = showEt,
                                            showRor = showRor,
                                            onToggleBt = { showBt = !showBt },
                                            onToggleEt = { showEt = !showEt },
                                            onToggleRor = { showRor = !showRor },
                                            modifier = Modifier.padding(horizontal = 16.dp),
                                        )
                                    }
                                    Column(
                                        Modifier
                                            .weight(0.4f)
                                            .fillMaxSize()
                                            .verticalScroll(rememberScrollState())
                                            .padding(horizontal = 8.dp),
                                    ) {
                                        PhaseCard(p)
                                        MarkerCard(p)
                                        RoastCard(p)
                                        EventsCard(p, eventsExpanded) { eventsExpanded = !eventsExpanded }
                                        Spacer(Modifier.height(16.dp))
                                    }
                                }
                            } else {
                                // Portrait: single scrollable column
                                Column(
                                    Modifier
                                        .fillMaxSize()
                                        .verticalScroll(rememberScrollState()),
                                ) {
                                    ProfileChart(
                                        p,
                                        Modifier
                                            .fillMaxWidth()
                                            .height(320.dp),
                                        showBt = showBt,
                                        showEt = showEt,
                                        showRor = showRor,
                                    )
                                    LegendRow(
                                        showBt = showBt,
                                        showEt = showEt,
                                        showRor = showRor,
                                        onToggleBt = { showBt = !showBt },
                                        onToggleEt = { showEt = !showEt },
                                        onToggleRor = { showRor = !showRor },
                                        modifier = Modifier.padding(horizontal = 16.dp),
                                    )
                                    PhaseCard(p)
                                    MarkerCard(p)
                                    RoastCard(p)
                                    EventsCard(p, eventsExpanded) { eventsExpanded = !eventsExpanded }
                                    Spacer(Modifier.height(16.dp))
                                }
                            }
                        }
                    }
                }
                1 -> {
                    // Sensory tab
                    SensoryTab(
                        uuid = uuid,
                        onRecordCupping = onRecordCupping,
                        onEditCupping = onEditCupping,
                        onEditRadar = onEditRadar,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Legend — tappable curve toggles
// ---------------------------------------------------------------------------

@Composable
private fun LegendRow(
    showBt: Boolean,
    showEt: Boolean,
    showRor: Boolean,
    onToggleBt: () -> Unit,
    onToggleEt: () -> Unit,
    onToggleRor: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        LegendChip(BtRed, stringResource(R.string.legend_bt), showBt, onToggleBt)
        LegendChip(EtBlue, stringResource(R.string.legend_et), showEt, onToggleEt)
        LegendChip(RorGrey, stringResource(R.string.legend_ror), showRor, onToggleRor)
    }
}

@Composable
private fun LegendChip(
    color: Color,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val bgColor = if (selected) {
        color.copy(alpha = 0.18f)
    } else {
        Color.Transparent
    }
    val contentColor = if (selected) Cream else CreamDim
    val stateDesc = stringResource(if (selected) R.string.common_state_on else R.string.common_state_off)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier
            .semantics(mergeDescendants = true) {
                role = Role.Switch
                stateDescription = stateDesc
            }
            .clickable(onClick = onClick)
            .background(bgColor, shape = MaterialTheme.shapes.small)
            .padding(horizontal = 12.dp, vertical = 8.dp)
            .height(48.dp),
    ) {
        Box(
            Modifier
                .size(12.dp)
                .background(color.copy(alpha = if (selected) 1f else 0.3f), shape = MaterialTheme.shapes.extraSmall),
        )
        Text(label, style = MaterialTheme.typography.labelLarge, color = contentColor)
    }
}

// ---------------------------------------------------------------------------
// Info cards
// ---------------------------------------------------------------------------

@Composable
private fun InfoCard(title: String, content: @Composable () -> Unit) {
    Card(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, color = Caramel)
            Spacer(Modifier.height(8.dp))
            content()
        }
    }
}

/** Phase durations (DRY / MID / Dev) + RoR peak. */
@Composable
private fun PhaseCard(p: RoastProfile) {
    val rorPeak = p.ror_c_per_min.filterNotNull().maxOrNull()
    InfoCard(title = stringResource(R.string.card_phases)) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.phase_dry), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(fmt(p.phases.drying_s), style = MaterialTheme.typography.bodyMedium)
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.phase_mid), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(fmt(p.phases.maillard_s), style = MaterialTheme.typography.bodyMedium)
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.phase_dev), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(fmt(p.phases.development_s), style = MaterialTheme.typography.bodyMedium)
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.phase_total), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(fmt(p.phases.total_s), style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.phase_ror_peak), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    rorPeak?.let { stringResource(R.string.fmt_ror, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                    color = RorGrey,
                )
            }
        }
    }
}

/** Markers: CHARGE, DRY, FCs, DROP, COOL, TP — with times (relative to CHARGE) and temps. */
@Composable
private fun MarkerCard(p: RoastProfile) {
    val chargeTime = p.markers["CHARGE"]?.time_s
    val tOffset = chargeTime ?: 0.0

    // TP: prefer the backend-supplied marker; fall back to the BT minimum over
    // post-CHARGE samples only (time_s >= 0 relative to CHARGE), so a warm-up
    // dip at ambient temperature is never mistaken for the turning point.
    val tpMarker = p.markers["TP"]
    val tpIndex = if (tpMarker == null && p.bt_c.isNotEmpty()) {
        p.bt_c.indices
            .filter { i -> (p.times_s.getOrNull(i) ?: Double.NEGATIVE_INFINITY) - tOffset >= 0.0 }
            .minByOrNull { p.bt_c[it] }
    } else {
        null
    }
    val tpAbsTime = tpMarker?.time_s ?: tpIndex?.let { p.times_s.getOrNull(it) }
    val tpTemp = tpMarker?.temp_bt_c ?: tpIndex?.let { p.bt_c[it] }

    // Ordered marker display
    val orderedMarkers = listOf("CHARGE", "TP", "DRY", "FCs", "DROP", "COOL")
    val displayMarkers = orderedMarkers.mapNotNull { name ->
        when (name) {
            "TP" -> tpAbsTime?.let { Triple("TP", it, tpTemp) }
            else -> p.markers[name]?.let { Triple(name, it.time_s, it.temp_bt_c) }
        }
    }

    InfoCard(title = stringResource(R.string.card_markers)) {
        if (displayMarkers.isEmpty()) {
            Text(stringResource(R.string.markers_none), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
            return@InfoCard
        }
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            // Header row
            Row(Modifier.fillMaxWidth()) {
                Text("", Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CreamDim)
                Text(stringResource(R.string.markers_time), Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CreamDim)
                Text(stringResource(R.string.markers_bt), Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = CreamDim)
            }
            displayMarkers.forEach { (name, absTime, temp) ->
                val relTime = absTime - tOffset
                Row(Modifier.fillMaxWidth()) {
                    Text(
                        name,
                        Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (name == "TP") Caramel else Cream,
                    )
                    Text(
                        fmtRel(relTime),
                        Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        temp?.let { stringResource(R.string.fmt_temp_short, it) } ?: "--",
                        Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
    }
}

/** Roast metadata: weights + loss %, ambient, sampling, machine, Artisan version. */
@Composable
private fun RoastCard(p: RoastProfile) {
    val lossPct = if (
        p.green_weight_g != null && p.roasted_weight_g != null && p.green_weight_g > 0
    ) {
        (p.green_weight_g - p.roasted_weight_g) / p.green_weight_g * 100.0
    } else null

    InfoCard(title = stringResource(R.string.card_roast)) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            // Weights + loss
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_green), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.green_weight_g?.let { stringResource(R.string.fmt_grams, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_roasted), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.roasted_weight_g?.let { stringResource(R.string.fmt_grams, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_loss), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    lossPct?.let { stringResource(R.string.fmt_percent, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (lossPct != null && lossPct > 0) Caramel else Cream,
                )
            }
            Spacer(Modifier.height(4.dp))
            // Ambient conditions
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_ambient), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.meta.ambient_temp_c?.let { stringResource(R.string.fmt_celsius, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_sampling), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.meta.sampling_interval_s?.let { stringResource(R.string.fmt_seconds, it) } ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Spacer(Modifier.height(4.dp))
            // Machine + Artisan version
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_machine), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.meta.roastertype ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.roast_artisan), style = MaterialTheme.typography.bodyMedium, color = CreamDim)
                Text(
                    p.meta.artisan_version ?: "--",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

/** Collapsible events list. Header shows the event count. */
@Composable
private fun EventsCard(
    p: RoastProfile,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    val chargeTime = p.markers["CHARGE"]?.time_s
    val tOffset = chargeTime ?: 0.0
    val events = p.events

    Card(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Column(Modifier.padding(16.dp)) {
            // Header (always visible, tappable)
            Row(
                Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggle)
                    .padding(vertical = 4.dp)
                    .height(48.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    stringResource(R.string.events_title_format, events.size),
                    style = MaterialTheme.typography.titleSmall,
                    color = Caramel,
                )
                Icon(
                    if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = stringResource(
                        if (expanded) R.string.common_collapse else R.string.common_expand,
                    ),
                    tint = CreamDim,
                )
            }

            AnimatedVisibility(visible = expanded) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Spacer(Modifier.height(4.dp))
                    if (events.isEmpty()) {
                        Text(
                            stringResource(R.string.events_none),
                            style = MaterialTheme.typography.bodyMedium,
                            color = CreamDim,
                        )
                    } else {
                        events.forEach { event ->
                            EventRow(event, tOffset)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EventRow(event: RoastEvent, tOffset: Double) {
    val relTime = event.time_s - tOffset
    val parts = buildList {
        add(fmtRel(relTime))
        event.type_label?.let { add(it) }
        event.slider_value?.let { add(stringResource(R.string.event_slider_format, it)) }
        event.label?.let { add(it) }
    }
    Text(
        parts.joinToString("  ·  "),
        style = MaterialTheme.typography.bodySmall,
        color = CreamDim,
    )
}

// ---------------------------------------------------------------------------
// Time formatting helpers
// ---------------------------------------------------------------------------

/** Format seconds as M:SS (non-negative). */
private fun fmt(sec: Double?): String {
    if (sec == null) return "--"
    val total = sec.toInt().coerceAtLeast(0)
    return "${total / 60}:${String.format("%02d", total % 60)}"
}

/** Format a relative time (seconds, may be negative) as M:SS or -M:SS. */
private fun fmtRel(sec: Double): String {
    val total = sec.roundToInt()
    val sign = if (total < 0) "-" else ""
    val a = abs(total)
    return "$sign${a / 60}:${String.format("%02d", a % 60)}"
}
