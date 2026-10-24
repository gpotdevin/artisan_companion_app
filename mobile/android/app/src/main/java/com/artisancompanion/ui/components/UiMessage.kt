package com.artisancompanion.ui.components

/** A user-facing message: string resource id + format arguments. */
data class UiMessage(val resId: Int, val args: List<Any> = emptyList())
