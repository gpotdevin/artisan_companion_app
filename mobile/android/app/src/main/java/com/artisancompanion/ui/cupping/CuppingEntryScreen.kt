package com.artisancompanion.ui.cupping

import android.app.DatePickerDialog
import android.widget.DatePicker
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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.R
import com.artisancompanion.data.Cupping
import com.artisancompanion.data.Repository
import com.artisancompanion.data.Scores
import com.artisancompanion.ui.components.UiMessage
import com.artisancompanion.ui.editor.RadarChart
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.CaramelBright
import com.artisancompanion.ui.theme.Cream
import com.artisancompanion.ui.theme.CreamDim
import com.artisancompanion.ui.theme.ErrorText
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.temporal.ChronoUnit
import kotlin.math.roundToInt

// ---------------------------------------------------------------------------
// Score key metadata
// ---------------------------------------------------------------------------

private val SCA_SCORE_KEYS = listOf(
    "fragrance_aroma", "flavor", "aftertaste", "acidity", "body",
    "balance", "uniformity", "clean_cup", "sweetness", "overall",
)

/** String resource for an SCA score key's label, or 0 to fall back to the raw key. */
private fun scaLabelRes(key: String): Int = when (key) {
    "fragrance_aroma" -> R.string.sca_fragrance_aroma
    "flavor" -> R.string.sca_flavor
    "aftertaste" -> R.string.sca_aftertaste
    "acidity" -> R.string.sca_acidity
    "body" -> R.string.sca_body
    "balance" -> R.string.sca_balance
    "uniformity" -> R.string.sca_uniformity
    "clean_cup" -> R.string.sca_clean_cup
    "sweetness" -> R.string.sca_sweetness
    "overall" -> R.string.sca_overall
    else -> 0
}

/** String resource for an SCA score key's short (radar) label, or 0 for the raw key. */
private fun scaShortLabelRes(key: String): Int = when (key) {
    "fragrance_aroma" -> R.string.sca_short_aroma
    "flavor" -> R.string.sca_short_flavor
    "aftertaste" -> R.string.sca_short_aftertaste
    "acidity" -> R.string.sca_short_acidity
    "body" -> R.string.sca_short_body
    "balance" -> R.string.sca_short_balance
    "uniformity" -> R.string.sca_short_uniformity
    "clean_cup" -> R.string.sca_short_clean
    "sweetness" -> R.string.sca_short_sweet
    "overall" -> R.string.sca_short_overall
    else -> 0
}

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

class CuppingEntryViewModel : ViewModel() {

    var uiState by mutableStateOf(CuppingEntryUiState())
        private set

    fun load(uuid: String, cuppingIndex: Int) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, uuid = uuid, cuppingIndex = cuppingIndex)

            // Fetch the roast date for rest-days computation.
            val profile = runCatching { Repository.getProfile(uuid) }.getOrNull()
            val roastDate = profile?.roast_date

            // Fetch the sensory record (may be null for unannotated roasts).
            val record = runCatching { Repository.getSensory(uuid) }.getOrNull()

            if (cuppingIndex >= 0) {
                // Edit mode: pre-fill from the existing cupping.
                val cupping = record?.cuppings?.getOrNull(cuppingIndex)
                if (cupping != null) {
                    val scores = mutableMapOf<String, Float>()
                    SCA_SCORE_KEYS.forEach { key ->
                        scores[key] = getScoreValue(cupping.scores, key)?.toFloat() ?: 0f
                    }
                    uiState = uiState.copy(
                        loading = false,
                        roastDate = roastDate,
                        date = cupping.date,
                        scores = scores,
                        defects = cupping.scores.defects?.toFloat() ?: 0f,
                        descriptors = cupping.descriptors,
                        notes = cupping.notes.orEmpty(),
                    )
                } else {
                    uiState = uiState.copy(loading = false, roastDate = roastDate, date = todayIso())
                }
            } else {
                // New cupping: default date to today, scores to 0.
                val scores = SCA_SCORE_KEYS.associateWith { 0f }.toMutableMap()
                uiState = uiState.copy(
                    loading = false,
                    roastDate = roastDate,
                    date = todayIso(),
                    scores = scores,
                    defects = 0f,
                    descriptors = emptyList(),
                    notes = "",
                )
            }
        }
    }

    fun setDate(date: String) {
        uiState = uiState.copy(date = date)
    }

    fun setScore(key: String, value: Float) {
        val next = uiState.scores.toMutableMap()
        next[key] = value
        uiState = uiState.copy(scores = next)
    }

    fun setDefects(value: Float) {
        uiState = uiState.copy(defects = value)
    }

    fun addDescriptor(text: String) {
        val trimmed = text.trim()
        if (trimmed.isNotEmpty() && trimmed !in uiState.descriptors) {
            uiState = uiState.copy(descriptors = uiState.descriptors + trimmed)
        }
    }

    fun removeDescriptor(text: String) {
        uiState = uiState.copy(descriptors = uiState.descriptors - text)
    }

    fun setNotes(text: String) {
        uiState = uiState.copy(notes = text)
    }

    fun requestDelete() {
        uiState = uiState.copy(showDeleteDialog = true)
    }

    fun cancelDelete() {
        uiState = uiState.copy(showDeleteDialog = false)
    }

    fun confirmDelete(onDeleted: () -> Unit) {
        val index = uiState.cuppingIndex
        uiState = uiState.copy(showDeleteDialog = false)
        if (index < 0) return
        viewModelScope.launch {
            runCatching { Repository.removeCupping(uiState.uuid, index) }
                .onSuccess { onDeleted() }
                .onFailure {
                    uiState = uiState.copy(error = UiMessage(R.string.common_error_format, listOf(it.message.orEmpty())))
                }
        }
    }

    fun save(onSaved: () -> Unit) {
        val date = uiState.date.trim()
        if (date.isEmpty()) {
            uiState = uiState.copy(error = UiMessage(R.string.error_date_required))
            return
        }
        // Validate date format.
        try {
            LocalDate.parse(date, DateTimeFormatter.ISO_LOCAL_DATE)
        } catch (e: DateTimeParseException) {
            uiState = uiState.copy(error = UiMessage(R.string.error_date_format))
            return
        }

        viewModelScope.launch {
            uiState = uiState.copy(saving = true, error = null)
            val cupping = buildCupping(date)
            val result = if (uiState.cuppingIndex >= 0) {
                runCatching { Repository.editCupping(uiState.uuid, uiState.cuppingIndex, cupping) }
            } else {
                runCatching { Repository.addCupping(uiState.uuid, cupping) }
            }
            result
                .onSuccess { onSaved() }
                .onFailure {
                    uiState = uiState.copy(
                        saving = false,
                        error = UiMessage(R.string.common_error_format, listOf(it.message ?: "")),
                    )
                }
        }
    }

    private fun buildCupping(date: String): Cupping {
        fun score(key: String): Double = uiState.scores[key]?.toDouble() ?: 0.0
        return Cupping(
            date = date,
            scores = Scores(
                fragrance_aroma = score("fragrance_aroma"),
                flavor = score("flavor"),
                aftertaste = score("aftertaste"),
                acidity = score("acidity"),
                body = score("body"),
                balance = score("balance"),
                uniformity = score("uniformity"),
                clean_cup = score("clean_cup"),
                sweetness = score("sweetness"),
                overall = score("overall"),
                defects = uiState.defects.toDouble(),
                total = null,
            ),
            descriptors = uiState.descriptors.toList(),
            notes = uiState.notes.trim().ifBlank { null },
        )
    }

    private fun getScoreValue(scores: Scores, key: String): Double? = when (key) {
        "fragrance_aroma" -> scores.fragrance_aroma
        "flavor" -> scores.flavor
        "aftertaste" -> scores.aftertaste
        "acidity" -> scores.acidity
        "body" -> scores.body
        "balance" -> scores.balance
        "uniformity" -> scores.uniformity
        "clean_cup" -> scores.clean_cup
        "sweetness" -> scores.sweetness
        "overall" -> scores.overall
        else -> null
    }
}

data class CuppingEntryUiState(
    val uuid: String = "",
    val cuppingIndex: Int = -1,
    val roastDate: String? = null,
    val date: String = "",
    val scores: Map<String, Float> = emptyMap(),
    val defects: Float = 0f,
    val descriptors: List<String> = emptyList(),
    val notes: String = "",
    val loading: Boolean = true,
    val saving: Boolean = false,
    val error: UiMessage? = null,
    val showDeleteDialog: Boolean = false,
) {
    /** Live total: round(max(0, sum of 10 scores - defects), 2). */
    val liveTotal: Double
        get() {
            val sum = SCA_SCORE_KEYS.sumOf { (scores[it] ?: 0f).toDouble() }
            val raw = sum - defects.toDouble()
            return (kotlin.math.max(0.0, raw) * 100).roundToInt() / 100.0
        }

    /** Days between roast date and cupping date (null if either is missing). */
    val restDays: Int?
        get() {
            val rd = roastDate ?: return null
            return try {
                val roast = LocalDate.parse(rd, DateTimeFormatter.ISO_LOCAL_DATE)
                val cup = LocalDate.parse(date, DateTimeFormatter.ISO_LOCAL_DATE)
                ChronoUnit.DAYS.between(roast, cup).toInt()
            } catch (e: DateTimeParseException) {
                null
            }
        }
}

private fun todayIso(): String = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE)

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CuppingEntryScreen(
    uuid: String,
    cuppingIndex: Int,
    onBack: () -> Unit,
    onSaved: () -> Unit,
) {
    val viewModel: CuppingEntryViewModel = viewModel()
    val state = viewModel.uiState
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(uuid, cuppingIndex) { viewModel.load(uuid, cuppingIndex) }

    val isEdit = cuppingIndex >= 0
    val title = stringResource(if (isEdit) R.string.cupping_edit_title else R.string.cupping_new_title)
    val cuppingSavedMessage = stringResource(R.string.msg_cupping_saved)
    val cuppingDeletedMessage = stringResource(R.string.msg_cupping_deleted)

    // -- Delete confirmation --
    if (state.showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { viewModel.cancelDelete() },
            title = { Text(stringResource(R.string.dialog_delete_cupping_title)) },
            text = { Text(stringResource(R.string.dialog_delete_cupping_simple)) },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.confirmDelete {
                            scope.launch {
                                snackbarHostState.showSnackbar(cuppingDeletedMessage)
                                onBack()
                            }
                        }
                    },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = ErrorText,
                    ),
                ) { Text(stringResource(R.string.common_delete)) }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.cancelDelete() }) {
                    Text(stringResource(R.string.common_cancel))
                }
            },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.common_back))
                    }
                },
                actions = {
                    if (isEdit) {
                        IconButton(onClick = { viewModel.requestDelete() }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = stringResource(R.string.cd_delete_cupping),
                                tint = MaterialTheme.colorScheme.error,
                            )
                        }
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
                // Two-column layout on wide screens
                Row(Modifier.weight(1f).fillMaxSize()) {
                    Column(
                        Modifier
                            .weight(0.55f)
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        DateAndRestSection(state, viewModel)
                        ScoreSlidersSection(state, viewModel)
                        DefectsSliderSection(state, viewModel)
                        LiveTotalCard(total = state.liveTotal)
                    }
                    Column(
                        Modifier
                            .weight(0.45f)
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        LiveRadarPreview(scores = state.scores)
                        DescriptorsSection(state, viewModel)
                        NotesSection(state, viewModel)
                    }
                }
            } else {
                // Single column on narrow screens
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    DateAndRestSection(state, viewModel)
                    ScoreSlidersSection(state, viewModel)
                    DefectsSliderSection(state, viewModel)
                    LiveTotalCard(total = state.liveTotal)
                    LiveRadarPreview(scores = state.scores)
                    DescriptorsSection(state, viewModel)
                    NotesSection(state, viewModel)
                }
            }

            // Error message
            state.error?.let { err ->
                Text(
                    stringResource(err.resId, *err.args.toTypedArray()),
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
                            snackbarHostState.showSnackbar(cuppingSavedMessage)
                            onSaved()
                        }
                    }
                },
                enabled = !state.saving && state.date.isNotBlank(),
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
                    Text(
                        stringResource(
                            if (isEdit) R.string.action_update_cupping else R.string.action_save_cupping,
                        ),
                    )
                }
            }
        }
        }
    }
}

// ---------------------------------------------------------------------------
// Date + rest days
// ---------------------------------------------------------------------------

@Composable
private fun DateAndRestSection(
    state: CuppingEntryUiState,
    viewModel: CuppingEntryViewModel,
) {
    val context = LocalContext.current

    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                stringResource(R.string.cupping_date_label),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )

            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = state.date,
                    onValueChange = { viewModel.setDate(it) },
                    label = { Text(stringResource(R.string.cupping_date_hint)) },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(
                    onClick = {
                        val initial = try {
                            LocalDate.parse(state.date, DateTimeFormatter.ISO_LOCAL_DATE)
                        } catch (e: DateTimeParseException) {
                            LocalDate.now()
                        }
                        DatePickerDialog(
                            context,
                            { _: DatePicker, year: Int, month: Int, dayOfMonth: Int ->
                                val picked = LocalDate.of(year, month + 1, dayOfMonth)
                                viewModel.setDate(picked.format(DateTimeFormatter.ISO_LOCAL_DATE))
                            },
                            initial.year,
                            initial.monthValue - 1,
                            initial.dayOfMonth,
                        ).show()
                    },
                    modifier = Modifier.height(48.dp),
                ) {
                    Icon(
                        Icons.Default.CalendarMonth,
                        contentDescription = stringResource(R.string.cd_pick_date),
                    )
                }
            }

            // Rest days display
            val restDays = state.restDays
            if (restDays != null) {
                Text(
                    if (restDays >= 0) {
                        stringResource(R.string.rest_days_after, restDays)
                    } else {
                        stringResource(R.string.rest_days_before, -restDays)
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = CaramelBright,
                )
            } else if (state.roastDate != null) {
                Text(
                    stringResource(R.string.rest_days_hint),
                    style = MaterialTheme.typography.bodySmall,
                    color = CreamDim,
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Score sliders
// ---------------------------------------------------------------------------

@Composable
private fun ScoreSlidersSection(
    state: CuppingEntryUiState,
    viewModel: CuppingEntryViewModel,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                stringResource(R.string.sca_scores_title),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )
            SCA_SCORE_KEYS.forEach { key ->
                val labelRes = scaLabelRes(key)
                ScoreSlider(
                    label = if (labelRes != 0) stringResource(labelRes) else key,
                    value = state.scores[key] ?: 0f,
                    onValueChange = { viewModel.setScore(key, it) },
                )
            }
        }
    }
}

@Composable
private fun ScoreSlider(
    label: String,
    value: Float,
    onValueChange: (Float) -> Unit,
) {
    Column {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(label, style = MaterialTheme.typography.bodyMedium, color = Cream)
            Text(
                "%.1f".format(value),
                style = MaterialTheme.typography.bodyMedium,
                color = CaramelBright,
            )
        }
        Slider(
            value = value,
            onValueChange = onValueChange,
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

// ---------------------------------------------------------------------------
// Defects penalty slider
// ---------------------------------------------------------------------------

@Composable
private fun DefectsSliderSection(
    state: CuppingEntryUiState,
    viewModel: CuppingEntryViewModel,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                stringResource(R.string.defects_penalty_title),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )
            ScoreSlider(
                label = stringResource(R.string.defects_penalty_label),
                value = state.defects,
                onValueChange = { viewModel.setDefects(it) },
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Live total
// ---------------------------------------------------------------------------

@Composable
private fun LiveTotalCard(total: Double) {
    Card(Modifier.fillMaxWidth()) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                stringResource(R.string.total_score_label),
                style = MaterialTheme.typography.titleMedium,
                color = Cream,
            )
            Text(
                stringResource(R.string.fmt_two_decimals, total),
                style = MaterialTheme.typography.headlineMedium,
                color = CaramelBright,
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Live radar preview
// ---------------------------------------------------------------------------

@Composable
private fun LiveRadarPreview(scores: Map<String, Float>) {
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
            val labels = SCA_SCORE_KEYS.map { key ->
                val labelRes = scaShortLabelRes(key)
                if (labelRes != 0) stringResource(labelRes) else key
            }
            val values = SCA_SCORE_KEYS.map { (scores[it] ?: 0f).toDouble() }
            RadarChart(
                labels = labels,
                values = values,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Descriptors
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun DescriptorsSection(
    state: CuppingEntryUiState,
    viewModel: CuppingEntryViewModel,
) {
    var showLexiconSheet by remember { mutableStateOf(false) }
    var freeText by remember { mutableStateOf("") }
    val context = LocalContext.current
    val lexicon = remember { context.resources.getStringArray(R.array.coffee_lexicon).toList() }

    if (showLexiconSheet) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(
            onDismissRequest = { showLexiconSheet = false },
            sheetState = sheetState,
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(
                    stringResource(R.string.descriptor_add_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = Cream,
                )

                // Free text input
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = freeText,
                        onValueChange = { freeText = it },
                        label = { Text(stringResource(R.string.descriptor_free_text)) },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(
                        onClick = {
                            if (freeText.isNotBlank()) {
                                viewModel.addDescriptor(freeText)
                                freeText = ""
                            }
                        },
                        modifier = Modifier.height(48.dp),
                    ) {
                        Icon(
                            Icons.Default.Add,
                            contentDescription = stringResource(R.string.cd_add_descriptor),
                        )
                    }
                }

                Text(
                    stringResource(R.string.descriptor_lexicon),
                    style = MaterialTheme.typography.titleSmall,
                    color = Caramel,
                )

                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    lexicon.forEach { word ->
                        val selected = word in state.descriptors
                        FilterChip(
                            selected = selected,
                            onClick = {
                                if (selected) viewModel.removeDescriptor(word)
                                else viewModel.addDescriptor(word)
                            },
                            label = { Text(word) },
                            leadingIcon = if (selected) {
                                { Icon(Icons.Default.Check, contentDescription = null) }
                            } else null,
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Caramel.copy(alpha = 0.2f),
                                selectedLabelColor = CaramelBright,
                            ),
                        )
                    }
                }

                Spacer(Modifier.height(16.dp))
            }
        }
    }

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
                    stringResource(R.string.descriptors_title),
                    style = MaterialTheme.typography.titleSmall,
                    color = Caramel,
                )
                TextButton(
                    onClick = { showLexiconSheet = true },
                    modifier = Modifier.height(48.dp),
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text(stringResource(R.string.common_add))
                }
            }

            if (state.descriptors.isEmpty()) {
                Text(
                    stringResource(R.string.descriptors_none),
                    style = MaterialTheme.typography.bodySmall,
                    color = CreamDim,
                )
            } else {
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    state.descriptors.forEach { d ->
                        AssistChip(
                            onClick = { viewModel.removeDescriptor(d) },
                            label = { Text(d) },
                            trailingIcon = {
                                Icon(
                                    Icons.Default.Close,
                                    contentDescription = stringResource(R.string.cd_remove_descriptor, d),
                                    modifier = Modifier.height(18.dp),
                                )
                            },
                            colors = AssistChipDefaults.assistChipColors(
                                containerColor = Caramel.copy(alpha = 0.15f),
                                labelColor = CaramelBright,
                            ),
                        )
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Notes
// ---------------------------------------------------------------------------

@Composable
private fun NotesSection(
    state: CuppingEntryUiState,
    viewModel: CuppingEntryViewModel,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                stringResource(R.string.notes_label),
                style = MaterialTheme.typography.titleSmall,
                color = Caramel,
            )
            OutlinedTextField(
                value = state.notes,
                onValueChange = { viewModel.setNotes(it) },
                label = { Text(stringResource(R.string.notes_hint)) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp),
                maxLines = 5,
            )
        }
    }
}
