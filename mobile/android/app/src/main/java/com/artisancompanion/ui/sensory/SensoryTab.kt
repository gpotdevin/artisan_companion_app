package com.artisancompanion.ui.sensory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.R
import com.artisancompanion.data.Cupping
import com.artisancompanion.data.Repository
import com.artisancompanion.data.SensoryRecord
import com.artisancompanion.data.SensoryUpdate
import com.artisancompanion.ui.components.UiMessage
import com.artisancompanion.ui.editor.RadarChart
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.CaramelBright
import com.artisancompanion.ui.theme.Cream
import com.artisancompanion.ui.theme.CreamDim
import com.artisancompanion.ui.theme.ErrorText
import kotlinx.coroutines.launch

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

class SensoryTabViewModel : ViewModel() {

    var uiState by mutableStateOf(SensoryTabUiState())
        private set

    fun load(uuid: String) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, uuid = uuid, message = null)
            val record = runCatching { Repository.getSensory(uuid) }.getOrNull()
            val labels = runCatching { Repository.radarLabels() }.getOrDefault(emptyList())
            val defectKeys = runCatching { Repository.defectKeys() }.getOrDefault(emptyList())
            uiState = uiState.copy(
                loading = false,
                record = record,
                radarLabels = labels,
                defectKeys = defectKeys,
            )
        }
    }

    fun refresh() {
        if (uiState.uuid.isNotEmpty()) load(uiState.uuid)
    }

    fun requestDeleteCupping(index: Int) {
        uiState = uiState.copy(pendingDeleteCuppingIndex = index)
    }

    fun cancelDeleteCupping() {
        uiState = uiState.copy(pendingDeleteCuppingIndex = null)
    }

    fun confirmDeleteCupping() {
        val index = uiState.pendingDeleteCuppingIndex ?: return
        uiState = uiState.copy(pendingDeleteCuppingIndex = null)
        viewModelScope.launch {
            runCatching { Repository.removeCupping(uiState.uuid, index) }
                .onSuccess { rec ->
                    uiState = uiState.copy(record = rec, message = UiMessage(R.string.msg_cupping_deleted))
                }
                .onFailure {
                    uiState = uiState.copy(
                        message = UiMessage(R.string.common_error_format, listOf(it.message ?: "")),
                    )
                }
        }
    }

    fun requestDeleteRecord() {
        uiState = uiState.copy(showDeleteRecordDialog = true)
    }

    fun cancelDeleteRecord() {
        uiState = uiState.copy(showDeleteRecordDialog = false)
    }

    fun confirmDeleteRecord() {
        uiState = uiState.copy(showDeleteRecordDialog = false)
        viewModelScope.launch {
            runCatching { Repository.deleteSensory(uiState.uuid) }
                .onSuccess {
                    uiState = uiState.copy(record = null, message = UiMessage(R.string.msg_sensory_deleted))
                }
                .onFailure {
                    uiState = uiState.copy(
                        message = UiMessage(R.string.common_error_format, listOf(it.message ?: "")),
                    )
                }
        }
    }

    /** Toggle a defect flag: optimistic local update, persisted via the store.
     *  Auto-creates the sensory record if none exists yet. */
    fun toggleDefect(key: String) {
        viewModelScope.launch {
            // Ensure a record exists so defects can be toggled even before
            // the first cupping session is recorded.
            var record = uiState.record
            if (record == null) {
                record = runCatching { Repository.createSensory(uiState.uuid) }
                    .onFailure {
                        uiState = uiState.copy(
                            message = UiMessage(R.string.common_error_format, listOf(it.message ?: "")),
                        )
                        return@launch
                    }
                    .getOrNull() ?: return@launch
                uiState = uiState.copy(record = record)
            }
            val current = record.defects_observed
            val updated = current.toMutableMap().apply { put(key, current[key] != true) }
            uiState = uiState.copy(record = record.copy(defects_observed = updated))
            runCatching { Repository.updateSensory(uiState.uuid, SensoryUpdate(defects_observed = updated)) }
                .onSuccess { rec -> uiState = uiState.copy(record = rec) }
                .onFailure {
                    uiState = uiState.copy(
                        record = record,
                        message = UiMessage(R.string.common_error_format, listOf(it.message ?: "")),
                    )
                }
        }
    }

    fun clearMessage() {
        uiState = uiState.copy(message = null)
    }
}

data class SensoryTabUiState(
    val uuid: String = "",
    val record: SensoryRecord? = null,
    val radarLabels: List<String> = emptyList(),
    val defectKeys: List<String> = emptyList(),
    val loading: Boolean = true,
    val message: UiMessage? = null,
    val pendingDeleteCuppingIndex: Int? = null,
    val showDeleteRecordDialog: Boolean = false,
)

// ---------------------------------------------------------------------------
// Sensory tab content
// ---------------------------------------------------------------------------

@Composable
fun SensoryTab(
    uuid: String,
    onRecordCupping: () -> Unit,
    onEditCupping: (Int) -> Unit,
    onEditRadar: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val viewModel: SensoryTabViewModel = viewModel()
    val state = viewModel.uiState
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(uuid) { viewModel.load(uuid) }

    // Surface view-model messages (delete feedback, errors) as snackbars.
    val messageText = state.message?.let { msg -> stringResource(msg.resId, *msg.args.toTypedArray()) }
    LaunchedEffect(state.message) {
        val text = messageText ?: return@LaunchedEffect
        viewModel.clearMessage()
        scope.launch { snackbarHostState.showSnackbar(text) }
    }

    // Refresh when returning from full-screen editors (cupping/radar).
    // Skip the first ON_RESUME — it fires immediately when the observer is
    // added (lifecycle already RESUMED), racing the LaunchedEffect load below.
    val lifecycleOwner = LocalLifecycleOwner.current
    var skipFirstResume by remember { mutableStateOf(true) }
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                if (skipFirstResume) {
                    skipFirstResume = false
                } else {
                    viewModel.refresh()
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    // -- Delete cupping confirmation --
    state.pendingDeleteCuppingIndex?.let { index ->
        val cupping = state.record?.cuppings?.getOrNull(index)
        AlertDialog(
            onDismissRequest = { viewModel.cancelDeleteCupping() },
            title = { Text(stringResource(R.string.dialog_delete_cupping_title)) },
            text = {
                val date = cupping?.date
                Text(
                    if (date != null) {
                        stringResource(R.string.dialog_delete_cupping_message, date)
                    } else {
                        stringResource(R.string.dialog_delete_cupping_message_nodate)
                    },
                )
            },
            confirmButton = {
                TextButton(
                    onClick = { viewModel.confirmDeleteCupping() },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = ErrorText,
                    ),
                ) { Text(stringResource(R.string.common_delete)) }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.cancelDeleteCupping() }) {
                    Text(stringResource(R.string.common_cancel))
                }
            },
        )
    }

    // -- Delete record confirmation --
    if (state.showDeleteRecordDialog) {
        AlertDialog(
            onDismissRequest = { viewModel.cancelDeleteRecord() },
            title = { Text(stringResource(R.string.dialog_delete_record_title)) },
            text = {
                Text(stringResource(R.string.dialog_delete_record_message))
            },
            confirmButton = {
                TextButton(
                    onClick = { viewModel.confirmDeleteRecord() },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = ErrorText,
                    ),
                ) { Text(stringResource(R.string.common_delete)) }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.cancelDeleteRecord() }) {
                    Text(stringResource(R.string.common_cancel))
                }
            },
        )
    }

    Box(modifier.fillMaxSize()) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .padding(bottom = 88.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (state.loading) {
                Box(Modifier.fillMaxWidth().padding(32.dp), Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                // -- Radar section --
                RadarSection(
                    record = state.record,
                    labels = state.radarLabels,
                    onEditRadar = onEditRadar,
                )

                // -- Defects section --
                DefectsSection(
                    record = state.record,
                    defectKeys = state.defectKeys,
                    onToggleDefect = { viewModel.toggleDefect(it) },
                )

                // -- Cuppings section --
                CuppingsSection(
                    record = state.record,
                    onRecordCupping = onRecordCupping,
                    onEditCupping = onEditCupping,
                    onDeleteCupping = { viewModel.requestDeleteCupping(it) },
                )

                // -- Delete record --
                if (state.record != null) {
                    Spacer(Modifier.height(4.dp))
                    OutlinedButton(
                        onClick = { viewModel.requestDeleteRecord() },
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = ErrorText,
                        ),
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text(stringResource(R.string.action_delete_sensory))
                    }
                }

                Spacer(Modifier.height(8.dp))
            }
        }

        // -- FAB (only when a record exists) --
        if (!state.loading && state.record != null) {
            ExtendedFloatingActionButton(
                onClick = onRecordCupping,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp),
                containerColor = Caramel,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                icon = { Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_record_cupping)) },
                text = { Text(stringResource(R.string.action_record_cupping)) },
            )
        }

        // Feedback messages; sits above the FAB.
        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 88.dp),
        )
    }
}

// ---------------------------------------------------------------------------
// Radar section
// ---------------------------------------------------------------------------

@Composable
private fun RadarSection(
    record: SensoryRecord?,
    labels: List<String>,
    onEditRadar: () -> Unit,
) {
    val radar = record?.radar
    val radarValues = radar?.values.orEmpty()
    val radarLabels = radar?.labels?.ifEmpty { labels } ?: labels
    val hasValues = radarValues.any { it > 0.0 }

    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    stringResource(R.string.radar_title),
                    style = MaterialTheme.typography.titleSmall,
                    color = Caramel,
                )
                TextButton(onClick = onEditRadar, modifier = Modifier.height(48.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text(stringResource(R.string.action_edit_radar))
                }
            }

            if (hasValues && radarLabels.isNotEmpty()) {
                RadarChart(
                    labels = radarLabels,
                    values = radarValues,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp),
                )
            } else {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(120.dp),
                    Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            stringResource(R.string.radar_empty),
                            style = MaterialTheme.typography.bodyMedium,
                            color = CreamDim,
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            stringResource(R.string.radar_empty_hint),
                            style = MaterialTheme.typography.bodySmall,
                            color = CreamDim,
                        )
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Defects section
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun DefectsSection(
    record: SensoryRecord?,
    defectKeys: List<String>,
    onToggleDefect: (String) -> Unit,
) {
    val defects = record?.defects_observed.orEmpty()
    val activeDefects = defectKeys.filter { defects[it] == true }

    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                stringResource(R.string.defects_title),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )

            if (defectKeys.isEmpty()) {
                Text(
                    stringResource(R.string.defects_loading),
                    style = MaterialTheme.typography.bodySmall,
                    color = CreamDim,
                )
            } else {
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    defectKeys.forEach { key ->
                        val active = defects[key] == true
                        val labelRes = defectLabelRes(key)
                        FilterChip(
                            selected = active,
                            onClick = { onToggleDefect(key) },
                            label = { Text(if (labelRes != 0) stringResource(labelRes) else key) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.2f),
                                selectedLabelColor = ErrorText,
                                containerColor = CreamDim.copy(alpha = 0.08f),
                                labelColor = CreamDim,
                            ),
                        )
                    }
                }

                if (activeDefects.isEmpty()) {
                    Text(
                        stringResource(R.string.defects_none),
                        style = MaterialTheme.typography.bodySmall,
                        color = CreamDim,
                    )
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Cuppings section
// ---------------------------------------------------------------------------

@Composable
private fun CuppingsSection(
    record: SensoryRecord?,
    onRecordCupping: () -> Unit,
    onEditCupping: (Int) -> Unit,
    onDeleteCupping: (Int) -> Unit,
) {
    // Newest first; original indices are preserved for edit/delete callbacks.
    val cuppings = record?.cuppings.orEmpty()
        .mapIndexed { index, cupping -> index to cupping }
        .sortedByDescending { it.second.date }

    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                stringResource(R.string.cuppings_title),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )

            when {
                // Unannotated roast: prominent CTA
                record == null -> {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .padding(vertical = 16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Text(
                            stringResource(R.string.cuppings_empty_title),
                            style = MaterialTheme.typography.titleMedium,
                            color = Cream,
                        )
                        Text(
                            stringResource(R.string.cuppings_empty_hint),
                            style = MaterialTheme.typography.bodyMedium,
                            color = CreamDim,
                        )
                        Button(
                            onClick = onRecordCupping,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp),
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text(stringResource(R.string.action_record_first_cupping))
                        }
                    }
                }

                // Annotated but no cuppings
                cuppings.isEmpty() -> {
                    Text(
                        stringResource(R.string.cuppings_none),
                        style = MaterialTheme.typography.bodyMedium,
                        color = CreamDim,
                    )
                }

                // List cuppings (newest first, original indices kept)
                else -> {
                    cuppings.forEachIndexed { displayIndex, (index, c) ->
                        CuppingRow(
                            cupping = c,
                            onEdit = { onEditCupping(index) },
                            onDelete = { onDeleteCupping(index) },
                        )
                        if (displayIndex < cuppings.lastIndex) {
                            Spacer(Modifier.height(4.dp))
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CuppingRow(
    cupping: Cupping,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(Modifier.padding(12.dp)) {
            // Header: date + total + actions
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            cupping.date,
                            style = MaterialTheme.typography.titleSmall,
                            color = Cream,
                        )
                        cupping.days_after_roast?.let { days ->
                            Spacer(Modifier.width(8.dp))
                            AssistChip(
                                onClick = { },
                                label = {
                                    Text(
                                        stringResource(R.string.cupping_day_format, days),
                                        style = MaterialTheme.typography.labelSmall,
                                    )
                                },
                                colors = AssistChipDefaults.assistChipColors(
                                    containerColor = Caramel.copy(alpha = 0.15f),
                                    labelColor = CaramelBright,
                                ),
                            )
                        }
                    }
                    Text(
                        stringResource(
                            R.string.cupping_total_format,
                            cupping.scores.total?.let { stringResource(R.string.fmt_two_decimals, it) } ?: "--",
                        ),
                        style = MaterialTheme.typography.bodyMedium,
                        color = CaramelBright,
                    )
                }
                Row {
                    IconButton(onClick = onEdit, modifier = Modifier.height(48.dp)) {
                        Icon(
                            Icons.Default.Edit,
                            contentDescription = stringResource(R.string.cd_edit_cupping),
                            tint = CreamDim,
                        )
                    }
                    IconButton(onClick = onDelete, modifier = Modifier.height(48.dp)) {
                        Icon(
                            Icons.Default.Delete,
                            contentDescription = stringResource(R.string.cd_delete_cupping),
                            tint = ErrorText,
                        )
                    }
                }
            }

            // Descriptors
            if (cupping.descriptors.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    cupping.descriptors.forEach { d ->
                        AssistChip(
                            onClick = { },
                            label = {
                                Text(d, style = MaterialTheme.typography.labelSmall)
                            },
                            colors = AssistChipDefaults.assistChipColors(
                                containerColor = CreamDim.copy(alpha = 0.1f),
                                labelColor = CreamDim,
                            ),
                        )
                    }
                }
            }

            // Notes snippet
            cupping.notes?.takeIf { it.isNotBlank() }?.let { notes ->
                Spacer(Modifier.height(4.dp))
                Text(
                    notes,
                    style = MaterialTheme.typography.bodySmall,
                    color = CreamDim,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** String resource for a defect key, or 0 to fall back to the raw key. */
private fun defectLabelRes(key: String): Int = when (key) {
    "heavyFC" -> R.string.defect_heavy_fc
    "lowFC" -> R.string.defect_low_fc
    "lightCut" -> R.string.defect_light_cut
    "darkCut" -> R.string.defect_dark_cut
    "drops" -> R.string.defect_drops
    "oily" -> R.string.defect_oily
    "uneven" -> R.string.defect_uneven
    "tipping" -> R.string.defect_tipping
    "scorching" -> R.string.defect_scorching
    "divots" -> R.string.defect_divots
    else -> 0
}
