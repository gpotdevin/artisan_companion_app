package com.artisancompanion

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.artisancompanion.data.Repository
import com.artisancompanion.ui.editor.EditorScreen
import com.artisancompanion.ui.library.LibraryScreen
import com.artisancompanion.ui.settings.SettingsScreen
import com.artisancompanion.ui.viewer.ViewerScreen
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

@Composable
fun ArtisanCompanionApp() {
    val nav = rememberNavController()
    val context = LocalContext.current
    val filesDir = remember { context.getExternalFilesDir(null) ?: context.filesDir }
    val logsDir = remember { File(filesDir, "logs").absolutePath }
    val sensoryDir = remember { File(filesDir, "sensory").absolutePath }

    // Initialize the Python core (build roast index + open sensory store) once.
    var ready by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        runCatching { withContext(Dispatchers.IO) { Repository.init(logsDir, sensoryDir) } }
        ready = true
    }

    if (!ready) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    NavHost(navController = nav, startDestination = "library") {
        composable("library") {
            LibraryScreen(
                onOpenRoast = { uuid -> nav.navigate("viewer/$uuid") },
                onOpenSettings = { nav.navigate("settings") },
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
                onEditSensory = { nav.navigate("editor/$uuid") },
            )
        }
        composable(
            "editor/{uuid}",
            arguments = listOf(navArgument("uuid") { type = NavType.StringType }),
        ) { backStack ->
            val uuid = backStack.arguments?.getString("uuid") ?: return@composable
            EditorScreen(uuid = uuid, onBack = { nav.popBackStack() })
        }
        composable("settings") {
            SettingsScreen(logsDir = logsDir, onBack = { nav.popBackStack() })
        }
    }
}
