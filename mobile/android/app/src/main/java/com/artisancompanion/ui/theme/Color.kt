package com.artisancompanion.ui.theme

import androidx.compose.ui.graphics.Color

// ---------------------------------------------------------------------------
// Dark coffee palette (default theme)
// ---------------------------------------------------------------------------

val CoffeeBgDark = Color(0xFF17110E)
val CoffeeSurfaceDark = Color(0xFF241A14)
val CoffeeSurfaceVariantDark = Color(0xFF33261D)
val CaramelDark = Color(0xFFC98A4B)
val CaramelBrightDark = Color(0xFFE0A96D)
val CreamDark = Color(0xFFEDE0D4)
val CreamDimDark = Color(0xFFB8A894)
val ErrorTextDark = Color(0xFFFF8A75)
val MarkerDark = Color(0xFFF2E9DC)

// ---------------------------------------------------------------------------
// Light coffee palette (Settings → Display → Light)
// Same accent hue family with inverted surfaces; text colors keep >= 4.5:1.
// ---------------------------------------------------------------------------

val CoffeeBgLight = Color(0xFFEDE0D4)
val CoffeeSurfaceLight = Color(0xFFF7F0E6)
val CoffeeSurfaceVariantLight = Color(0xFFE7DCCB)
val CaramelLight = Color(0xFF7A4E1E)
val CaramelBrightLight = Color(0xFF6E4518)
val CreamLight = Color(0xFF241A14)
val CreamDimLight = Color(0xFF6B5A48)
val ErrorTextLight = Color(0xFFA93226)
val ErrorLight = Color(0xFFB03426)
val MarkerLight = Color(0xFF241A14)

// ---------------------------------------------------------------------------
// Theme-aware semantic colors. These read ThemeManager, so every @Composable
// that uses them recomposes when the theme changes in Settings.
// ---------------------------------------------------------------------------

val CoffeeBg: Color get() = if (ThemeManager.isDark) CoffeeBgDark else CoffeeBgLight
val CoffeeSurface: Color get() = if (ThemeManager.isDark) CoffeeSurfaceDark else CoffeeSurfaceLight
val CoffeeSurfaceVariant: Color get() = if (ThemeManager.isDark) CoffeeSurfaceVariantDark else CoffeeSurfaceVariantLight
val Caramel: Color get() = if (ThemeManager.isDark) CaramelDark else CaramelLight
val CaramelBright: Color get() = if (ThemeManager.isDark) CaramelBrightDark else CaramelBrightLight
val Cream: Color get() = if (ThemeManager.isDark) CreamDark else CreamLight
val CreamDim: Color get() = if (ThemeManager.isDark) CreamDimDark else CreamDimLight

// Error text on surfaces: 7.4:1 on CoffeeSurface in dark; 5.1:1 on cream in light.
val ErrorText: Color get() = if (ThemeManager.isDark) ErrorTextDark else ErrorTextLight

// Chart marker lines/labels: near-white on dark, dark coffee on light.
val MarkerWhite: Color get() = if (ThemeManager.isDark) MarkerDark else MarkerLight

/** Overlay that dims the pre-CHARGE warm-up region of the profile chart. */
val ChartDimOverlay: Color
    get() = if (ThemeManager.isDark) {
        CoffeeBgDark.copy(alpha = 0.55f)
    } else {
        CoffeeSurfaceDark.copy(alpha = 0.15f)
    }

// ---------------------------------------------------------------------------
// Fixed semantic curve colors — identical in both themes (design spec §10):
// BT red, ET blue, RoR grey. Curves are also distinguished by line weight.
// ---------------------------------------------------------------------------

val BtRed = Color(0xFFE0533D)
val EtBlue = Color(0xFF4A90D9)
val RorGrey = Color(0xFF707070)

// Phase shading (translucent tints, readable on both themes).
val PhaseDrying = Color(0x33FFC864)
val PhaseMaillard = Color(0x40C89664)
val PhaseDevelopment = Color(0x55966464)
