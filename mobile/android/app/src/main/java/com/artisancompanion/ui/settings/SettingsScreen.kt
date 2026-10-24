package com.artisancompanion.ui.settings

import android.content.Intent
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.artisancompanion.R
import com.artisancompanion.data.Export
import com.artisancompanion.data.FileImport
import com.artisancompanion.data.Repository
import com.artisancompanion.ui.components.BottomNavBar
import com.artisancompanion.ui.components.BottomTab
import com.artisancompanion.ui.components.UiMessage
import com.artisancompanion.ui.theme.ThemeManager
import com.artisancompanion.ui.theme.ThemeMode
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

private const val TAG = "ArtisanCompanion"

class SettingsViewModel : ViewModel() {

    var state by mutableStateOf(SettingsUiState())
        private set

    fun load() {
        viewModelScope.launch {
            runCatching { Repository.listRoasts().size }
                .onSuccess { count -> state = state.copy(roastCount = count) }
                .onFailure { e -> Log.e(TAG, "load roast count failed", e) }
        }
    }

    fun rebuild() {
        viewModelScope.launch {
            state = state.copy(busy = true, message = null)
            runCatching { Repository.rebuildIndex() }
                .onSuccess { result ->
                    state = state.copy(
                        busy = false,
                        roastCount = result.roast_count,
                        message = UiMessage(R.string.settings_index_rebuilt, listOf(result.roast_count)),
                    )
                }
                .onFailure { e ->
                    Log.e(TAG, "rebuildIndex failed", e)
                    state = state.copy(
                        busy = false,
                        message = UiMessage(R.string.common_error_format, listOf(e.message ?: "")),
                    )
                }
        }
    }

    fun onImported(count: Int) {
        viewModelScope.launch {
            runCatching { Repository.rebuildIndex() }
                .onSuccess { result ->
                    state = state.copy(
                        roastCount = result.roast_count,
                        message = UiMessage(
                            R.string.settings_imported,
                            listOf(count, result.roast_count),
                        ),
                    )
                }
                .onFailure { e -> Log.e(TAG, "rebuildIndex after import failed", e) }
        }
    }

    fun clearMessage() {
        state = state.copy(message = null)
    }
}

data class SettingsUiState(
    val roastCount: Int? = null,
    val busy: Boolean = false,
    val message: UiMessage? = null,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    logsDir: String,
    sensoryDir: String,
    onImported: (Int) -> Unit,
    onNavigateToTab: (BottomTab) -> Unit,
) {
    val viewModel: SettingsViewModel = viewModel()
    val state = viewModel.state
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }
    val exportOkMessage = stringResource(R.string.msg_export_ok)
    val exportFailedMessage = stringResource(R.string.msg_export_failed)

    LaunchedEffect(Unit) { viewModel.load() }

    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        if (uris.isNotEmpty()) {
            scope.launch {
                val n = FileImport.copyInto(context.contentResolver, uris, File(logsDir))
                viewModel.onImported(n)
                onImported(n)
            }
        }
    }

    // Surface view-model messages (rebuild / import results, errors) as snackbars.
    val messageText = state.message?.let { msg -> stringResource(msg.resId, *msg.args.toTypedArray()) }
    LaunchedEffect(state.message) {
        val text = messageText ?: return@LaunchedEffect
        viewModel.clearMessage()
        scope.launch { snackbarHostState.showSnackbar(text) }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text(stringResource(R.string.settings_title)) })
        },
        bottomBar = {
            BottomNavBar(
                selectedTab = BottomTab.Settings,
                onTabSelected = onNavigateToTab,
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Column(
            Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // -- Storage --
            SectionTitle(stringResource(R.string.settings_section_storage))
            PathRow(
                label = stringResource(R.string.settings_logs_folder),
                path = logsDir,
            )
            PathRow(
                label = stringResource(R.string.settings_sensory_folder),
                path = sensoryDir,
            )
            if (state.roastCount != null) {
                Text(
                    stringResource(R.string.settings_roast_count, state.roastCount),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            SettingsActionButton(
                label = stringResource(R.string.rebuild_index),
                icon = Icons.Default.Refresh,
                enabled = !state.busy,
                onClick = { viewModel.rebuild() },
            )

            // -- Import --
            SectionTitle(stringResource(R.string.settings_section_import))
            SettingsActionButton(
                label = stringResource(R.string.import_logs),
                icon = Icons.Default.UploadFile,
                enabled = !state.busy,
                onClick = { importLauncher.launch(arrayOf("*/*")) },
            )

            // -- Display --
            SectionTitle(stringResource(R.string.settings_section_display))
            Text(
                stringResource(R.string.settings_theme_label),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ThemeMode.entries.forEach { mode ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                        .clickable { ThemeManager.setMode(context, mode) },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(
                        selected = ThemeManager.mode == mode,
                        onClick = { ThemeManager.setMode(context, mode) },
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        stringResource(
                            if (mode == ThemeMode.DARK) R.string.theme_dark else R.string.theme_light,
                        ),
                    )
                }
            }

            // -- Data --
            SectionTitle(stringResource(R.string.settings_section_data))
            SettingsActionButton(
                label = stringResource(R.string.settings_export_sensory),
                icon = Icons.Default.Download,
                enabled = !state.busy,
                onClick = {
                    scope.launch {
                        val zipFile = File(File(context.cacheDir, "exports"), "sensory_store.zip")
                        val ok = withContext(Dispatchers.IO) {
                            Export.zipDirectory(File(sensoryDir), zipFile)
                        }
                        if (ok) {
                            val uri = FileProvider.getUriForFile(
                                context,
                                "${context.packageName}.fileprovider",
                                zipFile,
                            )
                            val send = Intent(Intent.ACTION_SEND).apply {
                                type = "application/zip"
                                putExtra(Intent.EXTRA_STREAM, uri)
                                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            }
                            runCatching {
                                context.startActivity(
                                    Intent.createChooser(
                                        send,
                                        context.getString(R.string.export_chooser_title),
                                    ),
                                )
                            }
                            snackbarHostState.showSnackbar(exportOkMessage)
                        } else {
                            snackbarHostState.showSnackbar(exportFailedMessage)
                        }
                    }
                },
            )

            // -- About --
            SectionTitle(stringResource(R.string.settings_section_about))
            val versionName = remember {
                runCatching {
                    @Suppress("DEPRECATION")
                    context.packageManager.getPackageInfo(context.packageName, 0).versionName
                }.getOrNull()
            }
            Text(
                stringResource(R.string.app_name),
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                stringResource(R.string.about_version, versionName ?: "?"),
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                stringResource(R.string.about_disclaimer),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                stringResource(R.string.about_license),
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                stringResource(R.string.about_license_text),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                stringResource(R.string.about_repo),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )

            if (state.busy) CircularProgressIndicator()
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(top = 8.dp),
    )
}

@Composable
private fun PathRow(label: String, path: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(path, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun SettingsActionButton(
    label: String,
    icon: ImageVector,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Icon(icon, contentDescription = null)
        Spacer(Modifier.width(8.dp))
        Text(label)
    }
}
