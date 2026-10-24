package com.artisancompanion.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Coffee
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.artisancompanion.R

/** Top-level destinations shown in the bottom navigation bar. */
enum class BottomTab(val route: String, val labelRes: Int) {
    Roasts("library", R.string.library_title),
    Settings("settings", R.string.settings_title),
}

@Composable
fun BottomNavBar(
    selectedTab: BottomTab,
    onTabSelected: (BottomTab) -> Unit,
) {
    NavigationBar {
        NavigationBarItem(
            selected = selectedTab == BottomTab.Roasts,
            onClick = { onTabSelected(BottomTab.Roasts) },
            icon = { Icon(Icons.Default.Coffee, contentDescription = null) },
            label = { Text(stringResource(BottomTab.Roasts.labelRes)) },
            alwaysShowLabel = true,
        )
        NavigationBarItem(
            selected = selectedTab == BottomTab.Settings,
            onClick = { onTabSelected(BottomTab.Settings) },
            icon = { Icon(Icons.Default.Settings, contentDescription = null) },
            label = { Text(stringResource(BottomTab.Settings.labelRes)) },
            alwaysShowLabel = true,
        )
    }
}
