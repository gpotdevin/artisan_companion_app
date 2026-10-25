package com.artisancompanion

import android.content.Context
import android.util.Log
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.artisancompanion.R
import com.artisancompanion.data.FileImport
import com.artisancompanion.data.Preferences
import com.artisancompanion.data.Repository
import com.artisancompanion.ui.components.BottomTab
import com.artisancompanion.ui.cupping.CuppingEntryScreen
import com.artisancompanion.ui.editor.EditorScreen
import com.artisancompanion.ui.library.LibraryScreen
import com.artisancompanion.ui.radar.RadarEditorScreen
import com.artisancompanion.ui.settings.SettingsScreen
import com.artisancompanion.ui.viewer.ViewerScreen
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

@Composable
fun ArtisanCompanionApp() {
    val nav = rememberNavController()
    val context = LocalContext.current

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // Initialize the Python core (resolve storage root, build roast index +
    // open sensory store). Transient failures are auto-retried; a persistent
    // failure shows a full-screen error with a Retry button instead of a
    // silently broken app. The resolved root is persisted so it never
    // silently changes between restarts.
    var storageRoot by remember { mutableStateOf<File?>(null) }
    var initError by remember { mutableStateOf<String?>(null) }
    var initAttempt by remember { mutableStateOf(0) }
    LaunchedEffect(initAttempt) {
        initError = null
        try {
            storageRoot = initCore(context.applicationContext)
        } catch (e: Exception) {
            Log.e(TAG, "Core init failed after $INIT_MAX_ATTEMPTS attempts", e)
            initError = e.message ?: "Unknown error"
        }
    }

    // Visible init failure -- never a dead-end screen.
    if (initError != null) {
        val error = initError ?: return
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.padding(32.dp),
            ) {
                Icon(
                    Icons.Default.ErrorOutline,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(48.dp),
                )
                Text(
                    stringResource(R.string.init_error_title),
                    style = MaterialTheme.typography.titleLarge,
                    textAlign = TextAlign.Center,
                )
                Text(
                    stringResource(R.string.init_error_message),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
                Text(
                    stringResource(R.string.common_error_format, error),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
                Button(
                    onClick = { initAttempt++ },
                    modifier = Modifier.height(48.dp),
                ) {
                    Text(stringResource(R.string.common_retry))
                }
            }
        }
        return
    }

    // Python core still initializing (root is set only on success).
    if (storageRoot == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val root = storageRoot!!
    val logsDir = remember(root) { File(root, "logs").absolutePath }
    val sensoryDir = remember(root) { File(root, "sensory").absolutePath }

    /** Show a snackbar message (used for import toasts). */
    val showSnackbar: (String) -> Unit = { message ->
        scope.launch { snackbarHostState.showSnackbar(message) }
    }

    val importResultFormat = stringResource(R.string.import_result_format)

    // Handle .alog files shared from other apps (ACTION_SEND / ACTION_VIEW).
    // The URI arrives via MainActivity.pendingShareUri — set before composition
    // on cold start, or pushed from onNewIntent when the app is already running.
    LaunchedEffect(root) {
        MainActivity.pendingShareUri.collect { uri ->
            if (uri == null) return@collect
            MainActivity.pendingShareUri.value = null
            try {
                val count = FileImport.copyInto(
                    context.contentResolver,
                    listOf(uri),
                    File(root, "logs"),
                )
                if (count > 0) {
                    Repository.rebuildIndex()
                    showSnackbar(importResultFormat.format(count))
                    nav.navigate("library") {
                        popUpTo("library") { saveState = true }
                        launchSingleTop = true
                    }
                } else {
                    showSnackbar(
                        context.getString(R.string.common_error_format, "Not an .alog file")
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Share import failed", e)
                showSnackbar(
                    context.getString(R.string.common_error_format, e.message ?: "Import failed")
                )
            }
        }
    }

    /** Navigate between top-level tabs. */
    val onNavigateToTab: (BottomTab) -> Unit = { tab ->
        nav.navigate(tab.route) {
            popUpTo("library") { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    Box(Modifier.fillMaxSize()) {
        NavHost(navController = nav, startDestination = "library") {
            composable("library") {
                LibraryScreen(
                    logsDir = logsDir,
                    onOpenRoast = { uuid -> nav.navigate("viewer/$uuid") },
                    onImported = { count -> showSnackbar(importResultFormat.format(count)) },
                    onNavigateToTab = onNavigateToTab,
                )
            }
            composable(
                "viewer/{uuid}",
                arguments = listOf(navArgument("uuid") { type = NavType.StringType }),
            ) { backStack ->
                val uuid = backStack.arguments?.getString("uuid") ?: return@composable
                ViewerScreen(
                    uuid = uuid,
                    onBack = { nav.popBackStack() },
                    onRecordCupping = { nav.navigate("cupping/$uuid") },
                    onEditCupping = { index -> nav.navigate("cupping/$uuid/$index") },
                    onEditRadar = { nav.navigate("radar/$uuid") },
                )
            }
            // Full-screen cupping entry (new).
            composable(
                "cupping/{uuid}",
                arguments = listOf(navArgument("uuid") { type = NavType.StringType }),
            ) { backStack ->
                val uuid = backStack.arguments?.getString("uuid") ?: return@composable
                CuppingEntryScreen(
                    uuid = uuid,
                    cuppingIndex = -1,
                    onBack = { nav.popBackStack() },
                    onSaved = { nav.popBackStack() },
                )
            }
            // Full-screen cupping entry (edit existing).
            composable(
                "cupping/{uuid}/{index}",
                arguments = listOf(
                    navArgument("uuid") { type = NavType.StringType },
                    navArgument("index") { type = NavType.IntType },
                ),
            ) { backStack ->
                val uuid = backStack.arguments?.getString("uuid") ?: return@composable
                val index = backStack.arguments?.getInt("index") ?: -1
                CuppingEntryScreen(
                    uuid = uuid,
                    cuppingIndex = index,
                    onBack = { nav.popBackStack() },
                    onSaved = { nav.popBackStack() },
                )
            }
            // Full-screen radar editor.
            composable(
                "radar/{uuid}",
                arguments = listOf(navArgument("uuid") { type = NavType.StringType }),
            ) { backStack ->
                val uuid = backStack.arguments?.getString("uuid") ?: return@composable
                RadarEditorScreen(
                    uuid = uuid,
                    onBack = { nav.popBackStack() },
                    onSaved = { nav.popBackStack() },
                )
            }
            // Legacy editor (kept for backward compatibility).
            composable(
                "editor/{uuid}",
                arguments = listOf(navArgument("uuid") { type = NavType.StringType }),
            ) { backStack ->
                val uuid = backStack.arguments?.getString("uuid") ?: return@composable
                EditorScreen(uuid = uuid, onBack = { nav.popBackStack() })
            }
            composable("settings") {
                SettingsScreen(
                    logsDir = logsDir,
                    sensoryDir = sensoryDir,
                    onImported = { count -> showSnackbar(importResultFormat.format(count)) },
                    onNavigateToTab = onNavigateToTab,
                )
            }
        }

        // Snackbar overlay - sits above the bottom nav bar area.
        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 72.dp),
        )
    }
}

// ---------------------------------------------------------------------------
// Core init
// ---------------------------------------------------------------------------

private const val TAG = "ArtisanCompanion"
private const val INIT_MAX_ATTEMPTS = 3
private const val INIT_RETRY_DELAY_MS = 500L
private const val ROOT_RESOLVE_ATTEMPTS = 5
private const val ROOT_RESOLVE_DELAY_MS = 200L

/**
 * Resolve the app-storage root. The persisted root is reused while it still
 * exists (a transient getExternalFilesDir(null) == null right after install
 * must never switch the app to another root, orphaning imported files).
 * Otherwise resolve fresh -- retrying the external dir a few times before
 * falling back to internal storage -- and persist the winner.
 */
private suspend fun resolveStorageRoot(context: Context): File = withContext(Dispatchers.IO) {
    val persisted = Preferences.getStorageRoot(context)
    if (persisted != null) {
        val dir = File(persisted)
        if (dir.isDirectory) return@withContext dir
    }
    var resolved: File? = null
    for (attempt in 0 until ROOT_RESOLVE_ATTEMPTS) {
        resolved = context.getExternalFilesDir(null)
        if (resolved != null) break
        if (attempt < ROOT_RESOLVE_ATTEMPTS - 1) delay(ROOT_RESOLVE_DELAY_MS)
    }
    val root = resolved ?: context.filesDir
    Preferences.setStorageRoot(context, root.absolutePath)
    root
}

/**
 * Initialize the Python core against the stable storage root, retrying
 * transient failures ([INIT_MAX_ATTEMPTS] times, [INIT_RETRY_DELAY_MS] apart).
 * Returns the resolved root on success; rethrows the last failure otherwise.
 */
private suspend fun initCore(context: Context): File {
    val root = resolveStorageRoot(context)
    val logsDir = File(root, "logs").absolutePath
    val sensoryDir = File(root, "sensory").absolutePath
    var lastError: Exception? = null
    for (attempt in 1..INIT_MAX_ATTEMPTS) {
        try {
            withContext(Dispatchers.IO) { Repository.init(logsDir, sensoryDir) }
            return root
        } catch (e: Exception) {
            lastError = e
            Log.e(TAG, "Python init attempt $attempt/$INIT_MAX_ATTEMPTS failed", e)
            if (attempt < INIT_MAX_ATTEMPTS) delay(INIT_RETRY_DELAY_MS)
        }
    }
    throw lastError ?: IllegalStateException("Python init failed")
}
