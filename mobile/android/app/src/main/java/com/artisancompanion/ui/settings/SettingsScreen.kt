package com.artisancompanion.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import com.artisancompanion.data.FileImport
import com.artisancompanion.data.Repository
import kotlinx.coroutines.launch
import java.io.File

class SettingsViewModel : ViewModel() {

    var state by mutableStateOf(SettingsUiState())
        private set

    fun rebuild() {
        viewModelScope.launch {
            state = state.copy(busy = true, message = null)
            runCatching { Repository.rebuildIndex() }
                .onSuccess { result ->
                    state = state.copy(
                        busy = false,
                        roastCount = result.roastCount,
                        message = "Index rebuilt: ${result.roastCount} roasts",
                    )
                }
                .onFailure { e ->
                    state = state.copy(busy = false, message = "Error: ${e.message}")
                }
        }
    }

    fun onImported(count: Int) {
        viewModelScope.launch {
            runCatching { Repository.rebuildIndex() }
                .onSuccess { result ->
                    state = state.copy(
                        roastCount = result.roastCount,
                        message = "Imported $count file(s). ${result.roastCount} roasts indexed.",
                    )
                }
        }
    }
}

data class SettingsUiState(
    val roastCount: Int? = null,
    val busy: Boolean = false,
    val message: String? = null,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(logsDir: String, onBack: () -> Unit) {
    val viewModel: SettingsViewModel = viewModel()
    val state = viewModel.uiState
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        if (uris.isNotEmpty()) {
            scope.launch {
                val n = FileImport.copyInto(context.contentResolver, uris, File(logsDir))
                viewModel.onImported(n)
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Storage", style = MaterialTheme.typography.titleMedium)
            Text(
                "Logs folder",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(logsDir, style = MaterialTheme.typography.bodySmall)

            Button(
                onClick = { importLauncher.launch(arrayOf("*/*")) },
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.UploadFile, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Import .alog files")
            }

            Button(
                onClick = { viewModel.rebuild() },
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.Refresh, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Rebuild roast index")
            }

            if (state.busy) CircularProgressIndicator()
            if (state.message != null) {
                Text(state.message!!, color = MaterialTheme.colorScheme.primary)
            }
            if (state.roastCount != null) {
                Text("Roasts indexed: ${state.roastCount}", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
