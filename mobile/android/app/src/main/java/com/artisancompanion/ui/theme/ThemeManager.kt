package com.artisancompanion.ui.theme

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.artisancompanion.data.Preferences

/** Theme selection: dark (default) or light. Never follows the system setting. */
enum class ThemeMode(val value: String) {
    DARK("dark"),
    LIGHT("light"),
}

/**
 * Holds the active theme as Compose state so the whole app recomposes when the
 * user changes it in Settings. The choice is persisted via [Preferences].
 */
object ThemeManager {

    var mode by mutableStateOf(ThemeMode.DARK)
        private set

    val isDark: Boolean get() = mode == ThemeMode.DARK

    /** Load the persisted theme. Call once from Activity.onCreate. */
    fun init(context: Context) {
        mode = when (Preferences.getThemeMode(context)) {
            ThemeMode.LIGHT.value -> ThemeMode.LIGHT
            else -> ThemeMode.DARK
        }
    }

    fun setMode(context: Context, newMode: ThemeMode) {
        Preferences.setThemeMode(context, newMode.value)
        mode = newMode
    }
}
