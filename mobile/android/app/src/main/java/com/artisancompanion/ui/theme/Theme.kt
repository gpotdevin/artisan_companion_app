package com.artisancompanion.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = CaramelDark,
    onPrimary = CoffeeBgDark,
    secondary = CaramelBrightDark,
    background = CoffeeBgDark,
    onBackground = CreamDark,
    surface = CoffeeSurfaceDark,
    onSurface = CreamDark,
    surfaceVariant = CoffeeSurfaceVariantDark,
    onSurfaceVariant = CreamDimDark,
    error = BtRed,
    // Dark text on the BtRed error chip: 4.9:1 (M3 default onError fails at 3.4:1).
    onError = CoffeeBgDark,
)

private val LightColors = lightColorScheme(
    primary = CaramelLight,
    onPrimary = CoffeeSurfaceLight,
    secondary = CaramelBrightLight,
    onSecondary = CoffeeSurfaceLight,
    background = CoffeeBgLight,
    onBackground = CreamLight,
    surface = CoffeeSurfaceLight,
    onSurface = CreamLight,
    surfaceVariant = CoffeeSurfaceVariantLight,
    onSurfaceVariant = CreamDimLight,
    error = ErrorLight,
    onError = CoffeeSurfaceLight,
)

/**
 * App theme. Dark coffee by default; the light scheme is selected from
 * Settings (never the system setting). No dynamic colors.
 */
@Composable
fun ArtisanCompanionTheme(
    darkTheme: Boolean = ThemeManager.isDark,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
