package com.artisancompanion.ui.library

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Badge
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LocalLifecycleOwner
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.data.Repository
import com.artisancompanion.data.RoastSummary
import kotlinx.coroutines.launch

class LibraryViewModel : ViewModel() {

    var uiState by mutableStateOf(LibraryUiState())
        private set

    fun load() {
        viewModelScope.launch {
            uiState = uiState.copy(loading = true, error = null)
            runCatching { Repository.listRoasts() }
                .onSuccess { roasts -> uiState = uiState.copy(loading = false, roasts = roasts) }
                .onFailure { e -> uiState = uiState.copy(loading = false, error = e.message ?: "Error") }
        }
    }

    fun onQuery(q: String) {
        uiState = uiState.copy(query = q)
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
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(
    onOpenRoast: (String) -> Unit,
    onOpenSettings: () -> Unit,
) {
    val viewModel: LibraryViewModel = viewModel()
    val state = viewModel.uiState

    // Reload whenever the screen returns to the foreground (e.g. after an
    // import + rebuild in Settings).
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) viewModel.load()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Roasts") },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::onQuery,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text("Search roasts...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                singleLine = true,
            )
            when {
                state.loading && state.roasts.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
                state.error != null && state.roasts.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) { Text(state.error ?: "Error") }
                state.filtered.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        Text("No roasts. Import .alog files from Settings.")
                    }
                else -> LazyColumn(Modifier.fillMaxSize()) {
                    items(state.filtered, key = { it.roast_uuid }) { roast ->
                        RoastCard(roast = roast, onClick = { onOpenRoast(roast.roast_uuid) })
                    }
                }
            }
        }
    }
}

@Composable
private fun RoastCard(roast: RoastSummary, onClick: () -> Unit) {
    Card(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                roast.title ?: roast.source_file ?: roast.roast_uuid,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (roast.beans != null) {
                Text(
                    roast.beans!!,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    roast.roast_date ?: "",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (roast.annotated) Badge { Text("CUPPED") }
                    if (roast.best_total != null) {
                        Badge { Text("Score ${"%.1f".format(roast.best_total)}") }
                    }
                }
            }
        }
    }
}
