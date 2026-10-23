package com.artisancompanion.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = Caramel,
    onPrimary = CoffeeBg,
    secondary = CaramelBright,
    background = CoffeeBg,
    onBackground = Cream,
    surface = CoffeeSurface,
    onSurface = Cream,
    surfaceVariant = CoffeeSurfaceVariant,
    onSurfaceVariant = CreamDim,
    error = BtRed,
)

@Composable
fun ArtisanCompanionTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColors,
        content = content,
    )
}
