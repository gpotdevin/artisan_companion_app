package com.artisancompanion

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.artisancompanion.data.PythonBridge
import com.artisancompanion.ui.theme.ArtisanCompanionTheme
import com.artisancompanion.ui.theme.ThemeManager
import kotlinx.coroutines.flow.MutableStateFlow

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Start embedded CPython (Chaquopy) and load the facade module.
        PythonBridge.ensureStarted(applicationContext)
        // Load the persisted theme before the first composition.
        ThemeManager.init(applicationContext)
        enableEdgeToEdge()
        // Cold start via "Share → Artisan Companion" or "Open with…".
        extractShareUri(intent)?.let { pendingShareUri.value = it }
        setContent {
            ArtisanCompanionTheme {
                ArtisanCompanionApp()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // App already running (singleTask): handle the incoming share.
        extractShareUri(intent)?.let { pendingShareUri.value = it }
    }

    companion object {
        /**
         * Holds a .alog content URI received via ACTION_SEND / ACTION_VIEW.
         * ArtisanCompanionApp collects this after the Python core is ready,
         * imports the file, then clears it. A StateFlow (not a plain var) so
         * the Compose layer reacts even when the app is already running.
         */
        val pendingShareUri = MutableStateFlow<Uri?>(null)

        /** Extract the shared file URI from a SEND/VIEW intent, or null. */
        private fun extractShareUri(intent: Intent): Uri? {
            if (intent.action != Intent.ACTION_SEND && intent.action != Intent.ACTION_VIEW) {
                return null
            }
            @Suppress("DEPRECATION") // minSdk 26; typed overload needs API 33
            return intent.getParcelableExtra(Intent.EXTRA_STREAM) ?: intent.data
        }
    }
}
