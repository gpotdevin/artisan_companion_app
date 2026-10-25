package com.artisancompanion.ui.library

import android.content.ContentResolver
import android.net.Uri
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
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
import com.artisancompanion.data.FileImport
import com.artisancompanion.data.Preferences
import com.artisancompanion.data.Repository
import com.artisancompanion.data.RoastSummary
import com.artisancompanion.ui.components.BottomNavBar
import com.artisancompanion.ui.components.BottomTab
import com.artisancompanion.ui.components.IntroOverlay
import com.artisancompanion.ui.components.OnboardingStep
import com.artisancompanion.ui.theme.ErrorText
import kotlinx.coroutines.launch
import java.io.File
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

private const val TAG = "ArtisanCompanion"

class LibraryViewModel : ViewModel() {

    var uiState by mutableStateOf(LibraryUiState())
        private set

    fun load() {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, error = null)
            runCatching { Repository.listRoasts() }
                .onSuccess { roasts -> uiState = uiState.copy(loading = false, roasts = roasts) }
                .onFailure { e ->
                    Log.e(TAG, "listRoasts failed", e)
                    uiState = uiState.copy(loading = false, error = e.message)
                }
        }
    }

    fun onQuery(q: String) {
        uiState = uiState.copy(query = q)
    }

    /**
     * Import picked .alog files, rebuild the roast index, then refresh the
     * list. listRoasts() reads the in-memory index, so a rebuild is required
     * for newly imported files to appear without an app restart.
     */
    fun importFiles(
        resolver: ContentResolver,
        uris: List<Uri>,
        logsDir: File,
        onImported: (Int) -> Unit = {},
    ) {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, error = null)
            runCatching {
                val count = FileImport.copyInto(resolver, uris, logsDir)
                Repository.rebuildIndex()
                count
            }
                .onSuccess { count ->
                    load()
                    onImported(count)
                }
                .onFailure { e ->
                    Log.e(TAG, "Import/rebuildIndex failed", e)
                    uiState = uiState.copy(loading = false, error = e.message)
                }
        }
    }
}

data class LibraryUiState(
    val roasts: List<RoastSummary> = emptyList(),
    val query: String = "",
    val loading: Boolean = true,
    val error: String? = null,
) {
    val filtered: List<RoastSummary>
        get() {
            val q = query.trim().lowercase()
            if (q.isEmpty()) return roasts
            return roasts.filter {
                it.title?.lowercase()?.contains(q) == true ||
                    it.source_file?.lowercase()?.contains(q) == true ||
                    it.beans?.lowercase()?.contains(q) == true ||
                    it.roast_date?.contains(q) == true
            }
        }

    /** Roasts grouped by year-month, newest month first, newest roast first within group. */
    val grouped: List<MonthGroup>
        get() {
            val sorted = filtered.sortedWith { a, b ->
                val dateCmp = (b.roast_date ?: "").compareTo(a.roast_date ?: "")
                if (dateCmp != 0) dateCmp
                else (b.source_file ?: "").compareTo(a.source_file ?: "")
            }
            return sorted
                .groupBy { monthKey(it.roast_date) }
                .toSortedMap(compareByDescending { key: String -> key })
                .map { (key, roasts) -> MonthGroup(key, roasts) }
        }
}

data class MonthGroup(val key: String, val roasts: List<RoastSummary>)

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

/** Extract "2026-10" from an ISO date string like "2026-10-24". */
private fun monthKey(dateStr: String?): String {
    if (dateStr.isNullOrEmpty()) return "0000-00" // sorts last in descending order
    return dateStr.take(7)
}

/** Format a month key ("2026-10") as a localized label ("October 2026" / "octobre 2026"). */
@Composable
private fun formatMonthLabel(key: String): String {
    if (key == "0000-00") return stringResource(R.string.library_unknown_month)
    return try {
        val parts = key.split("-")
        val yearMonth = YearMonth.of(parts[0].toInt(), parts[1].toInt())
        yearMonth.format(DateTimeFormatter.ofPattern("MMMM yyyy", Locale.getDefault()))
    } catch (e: Exception) {
        key
    }
}

/** Format an ISO date string for display, e.g. "2026-10-24" -> "24 Oct 2026". */
private fun formatDate(dateStr: String?): String {
    if (dateStr.isNullOrEmpty()) return ""
    return try {
        val date = LocalDate.parse(dateStr.take(10))
        date.format(DateTimeFormatter.ofPattern("d MMM yyyy", Locale.getDefault()))
    } catch (e: Exception) {
        dateStr
    }
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(
    logsDir: String,
    onOpenRoast: (String) -> Unit,
    onImported: (Int) -> Unit,
    onNavigateToTab: (BottomTab) -> Unit,
) {
    val viewModel: LibraryViewModel = viewModel()
    val state = viewModel.uiState
    val context = LocalContext.current

    // First-launch intro overlay (shown once, remembered in SharedPreferences).
    var showIntro by remember { mutableStateOf(!Preferences.isIntroShown(context)) }

    // SAF picker for the empty-state "Import .alog files" button.
    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        if (uris.isNotEmpty()) {
            viewModel.importFiles(context.contentResolver, uris, File(logsDir)) { count ->
                onImported(count)
            }
        }
    }

    // Reload whenever the screen returns to the foreground.
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) viewModel.load()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(Unit) { viewModel.load() }

    // Deferred import launch: the intro overlay's onImport sets showIntro=false
    // (removing the Dialog from composition) and then must launch the SAF picker.
    // Calling launch() in the same callback races the composition change; deferring
    // via LaunchedEffect lets the Dialog dismiss first, then the picker opens.
    var pendingImport by remember { mutableStateOf(false) }

    if (showIntro) {
        IntroOverlay(
            onImport = {
                Preferences.setIntroShown(context)
                showIntro = false
                pendingImport = true
            },
            onDismiss = {
                Preferences.setIntroShown(context)
                showIntro = false
            },
        )
    }

    LaunchedEffect(pendingImport) {
        if (pendingImport) {
            pendingImport = false
            importLauncher.launch(arrayOf("*/*"))
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text(stringResource(R.string.library_title)) })
        },
        bottomBar = {
            BottomNavBar(
                selectedTab = BottomTab.Roasts,
                onTabSelected = onNavigateToTab,
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            // Search field
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::onQuery,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text(stringResource(R.string.library_search_hint)) },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                singleLine = true,
            )

            when {
                // Initial load
                state.loading && state.roasts.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        CircularProgressIndicator()
                    }

                // Error on initial load
                state.error != null && state.roasts.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.padding(32.dp),
                        ) {
                            Text(state.error)
                            Button(onClick = { viewModel.load() }) { Text(stringResource(R.string.common_retry)) }
                        }
                    }

                // Empty library - onboarding
                state.roasts.isEmpty() && state.query.isEmpty() ->
                    EmptyState(
                        onImport = { importLauncher.launch(arrayOf("*/*")) },
                        modifier = Modifier.fillMaxSize(),
                    )

                // Search returned nothing
                state.filtered.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        Text(
                            stringResource(R.string.library_no_match, state.query),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }

                // Roast list with month grouping
                else -> RoastList(
                    groups = state.grouped,
                    onOpenRoast = onOpenRoast,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Empty state - onboarding card
// ---------------------------------------------------------------------------

@Composable
private fun EmptyState(
    onImport: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(
                    stringResource(R.string.app_name),
                    style = MaterialTheme.typography.headlineMedium,
                )
                Text(
                    stringResource(R.string.library_empty_subtitle),
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                // 3 steps
                Column(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    OnboardingStep(number = 1, text = stringResource(R.string.onboarding_step_import))
                    OnboardingStep(number = 2, text = stringResource(R.string.onboarding_step_browse))
                    OnboardingStep(number = 3, text = stringResource(R.string.onboarding_step_cupping))
                }

                Button(
                    onClick = onImport,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Default.UploadFile, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.import_logs))
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Roast list with sticky month headers
// ---------------------------------------------------------------------------

@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
@Composable
private fun RoastList(
    groups: List<MonthGroup>,
    onOpenRoast: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    // Unparsable roast whose parse error is shown in a bottom sheet.
    var errorRoast by remember { mutableStateOf<RoastSummary?>(null) }
    val sheetState = rememberModalBottomSheetState()

    LazyColumn(modifier = modifier) {
        groups.forEach { group ->
            stickyHeader(key = "header_${group.key}") {
                Text(
                    text = formatMonthLabel(group.key),
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.background)
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                )
            }
            items(group.roasts, key = { it.roast_uuid }) { roast ->
                RoastCard(
                    roast = roast,
                    onClick = {
                        // Unparsable roasts do not navigate; tapping shows the error.
                        if (roast.parse_ok) {
                            onOpenRoast(roast.roast_uuid)
                        } else {
                            errorRoast = roast
                        }
                    },
                )
            }
        }
    }

    // Full parse error for an unparsable roast (spec 7.2 / 13).
    errorRoast?.let { roast ->
        ModalBottomSheet(
            onDismissRequest = { errorRoast = null },
            sheetState = sheetState,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    stringResource(R.string.library_unparsable_title),
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    roast.source_file ?: roast.roast_uuid,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    roast.error_msg ?: stringResource(R.string.library_unknown_error),
                    style = MaterialTheme.typography.bodyMedium,
                    color = ErrorText,
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Roast card
// ---------------------------------------------------------------------------

@Composable
private fun RoastCard(roast: RoastSummary, onClick: () -> Unit) {
    val unparsable = !roast.parse_ok

    Card(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .then(if (unparsable) Modifier.alpha(0.5f) else Modifier)
            .clickable(onClick = onClick),
    ) {
        Column(Modifier.padding(16.dp)) {
            // Title row with status chip
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.weight(1f),
                ) {
                    if (unparsable) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = stringResource(R.string.cd_unparsable),
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(18.dp),
                        )
                    }
                    Text(
                        roast.title ?: roast.source_file ?: roast.roast_uuid,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Spacer(Modifier.width(8.dp))
                StatusChip(roast)
            }

            // Source filename
            if (!roast.source_file.isNullOrBlank()) {
                Text(
                    roast.source_file,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            // Beans
            if (roast.beans != null) {
                Text(
                    roast.beans,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            // Weights + drop temp + date row
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    buildRoastDetails(roast),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    formatDate(roast.roast_date),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

/** Build the detail line: "250g -> 215g . Drop 205C". */
@Composable
private fun buildRoastDetails(roast: RoastSummary): String {
    val parts = mutableListOf<String>()
    if (roast.green_weight_g != null && roast.roasted_weight_g != null) {
        parts.add(
            stringResource(
                R.string.library_detail_both,
                roast.green_weight_g.toInt(),
                roast.roasted_weight_g.toInt(),
            ),
        )
    } else if (roast.green_weight_g != null) {
        parts.add(stringResource(R.string.library_detail_green, roast.green_weight_g.toInt()))
    } else if (roast.roasted_weight_g != null) {
        parts.add(stringResource(R.string.library_detail_roasted, roast.roasted_weight_g.toInt()))
    }
    if (roast.drop_bt_c != null) {
        parts.add(stringResource(R.string.library_detail_drop, roast.drop_bt_c.toInt()))
    }
    return parts.joinToString(" \u00B7 ")
}

// ---------------------------------------------------------------------------
// Status chip
// ---------------------------------------------------------------------------

@Composable
private fun StatusChip(roast: RoastSummary) {
    when {
        !roast.parse_ok ->
            Chip(
                text = stringResource(R.string.status_unparsable),
                containerColor = MaterialTheme.colorScheme.error,
                contentColor = MaterialTheme.colorScheme.onError,
                icon = Icons.Default.Warning,
            )
        roast.annotated && roast.best_total != null ->
            Chip(
                text = stringResource(R.string.status_cupped_score, roast.best_total),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                icon = Icons.Default.CheckCircle,
            )
        roast.annotated ->
            Chip(
                text = stringResource(R.string.status_cupped),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                icon = Icons.Default.CheckCircle,
            )
        else ->
            Chip(
                text = stringResource(R.string.status_uncupped),
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            )
    }
}

@Composable
private fun Chip(
    text: String,
    containerColor: Color,
    contentColor: Color,
    icon: ImageVector? = null,
) {
    Surface(
        color = containerColor,
        contentColor = contentColor,
        shape = RoundedCornerShape(8.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            if (icon != null) {
                Icon(icon, contentDescription = null, modifier = Modifier.size(14.dp))
            }
            Text(text, style = MaterialTheme.typography.labelSmall)
        }
    }
}
