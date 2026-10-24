package com.artisancompanion.data

import android.content.Context
import android.util.Log
import com.chaquo.python.Python
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform

/**
 * Bridge to the embedded CPython (Chaquopy). The native UI never touches the
 * network; it calls the Python facade [api] which runs the artisan-companion
 * core in-process and returns JSON strings.
 *
 * All calls perform disk I/O (parsing .alog, SQLite), so they must run off the
 * main thread -- [Repository] wraps every call in Dispatchers.IO.
 */
object PythonBridge {

    @Volatile
    private var module: PyObject? = null

    /** Start CPython and load the facade module. Call once from Activity.onCreate. */
    fun ensureStarted(context: Context) {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context.applicationContext))
        }
        if (module == null) {
            module = Python.getInstance().getModule("api")
        }
    }

    private fun mod(): PyObject =
        module ?: throw IllegalStateException("PythonBridge not started - call ensureStarted() first")

    /** Call an api.* function that returns a JSON string. */
    fun callJson(name: String, vararg args: Any?): String =
        mod().callAttr(name, *args).toString()

    /** Like [callJson] but returns null on any Python/bridge error. */
    fun callJsonOrNull(name: String, vararg args: Any?): String? =
        try {
            callJson(name, *args)
        } catch (e: Exception) {
            Log.e("ArtisanCompanion", "Python call <$name> failed", e)
            null
        }
}
