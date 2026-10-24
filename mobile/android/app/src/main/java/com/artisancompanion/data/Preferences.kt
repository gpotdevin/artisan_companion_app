package com.artisancompanion.data

import android.content.Context
import android.content.SharedPreferences

/** App-level SharedPreferences: theme mode + one-shot flags (intro overlay). */
object Preferences {

    private const val FILE_NAME = "artisan_companion_prefs"
    private const val KEY_THEME_MODE = "theme_mode"
    private const val KEY_INTRO_SHOWN = "intro_shown"
    private const val KEY_STORAGE_ROOT = "storage_root"

    private fun prefs(context: Context): SharedPreferences =
        context.applicationContext.getSharedPreferences(FILE_NAME, Context.MODE_PRIVATE)

    /** "dark" (default) or "light". Never "system" — the theme is chosen in Settings. */
    fun getThemeMode(context: Context): String =
        prefs(context).getString(KEY_THEME_MODE, "dark") ?: "dark"

    fun setThemeMode(context: Context, mode: String) {
        prefs(context).edit().putString(KEY_THEME_MODE, mode).apply()
    }

    fun isIntroShown(context: Context): Boolean =
        prefs(context).getBoolean(KEY_INTRO_SHOWN, false)

    fun setIntroShown(context: Context) {
        prefs(context).edit().putBoolean(KEY_INTRO_SHOWN, true).apply()
    }

    /**
     * Absolute path of the resolved app-storage root (logs/ and sensory/ live
     * here). Persisted so the root never silently changes between restarts --
     * otherwise imported files could get split across two different roots.
     * Null until the first successful resolution.
     */
    fun getStorageRoot(context: Context): String? =
        prefs(context).getString(KEY_STORAGE_ROOT, null)

    fun setStorageRoot(context: Context, path: String) {
        prefs(context).edit().putString(KEY_STORAGE_ROOT, path).apply()
    }
}
