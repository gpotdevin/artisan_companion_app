package com.artisancompanion

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.artisancompanion.data.PythonBridge
import com.artisancompanion.ui.theme.ArtisanCompanionTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Start embedded CPython (Chaquopy) and load the facade module.
        PythonBridge.ensureStarted(applicationContext)
        enableEdgeToEdge()
        setContent {
            ArtisanCompanionTheme {
                ArtisanCompanionApp()
            }
        }
    }
}
