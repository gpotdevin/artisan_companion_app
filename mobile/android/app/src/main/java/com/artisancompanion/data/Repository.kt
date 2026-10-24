package com.artisancompanion.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Single access point for the UI. Every call is dispatched to Dispatchers.IO
 * (the Python core does disk I/O) and returns a parsed model.
 *
 * The JSON contract matches the FastAPI web app, so the native and web UIs are
 * interchangeable.
 */
object Repository {

    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
    }

    private suspend fun <T> io(block: () -> String, decode: (String) -> T): T =
        withContext(Dispatchers.IO) {
            try {
                decode(block())
            } catch (e: Exception) {
                // The PyException message embeds the full Python traceback,
                // so logcat shows exactly which api.* call failed and why.
                Log.e("ArtisanCompanion", "Repository call failed", e)
                throw e
            }
        }

    // -- lifecycle / index ---------------------------------------------------

    suspend fun init(logsDir: String, sensoryDir: String): InitResult =
        io({ PythonBridge.callJson("init", logsDir, sensoryDir) }, { json.decodeFromString(it) })

    suspend fun rebuildIndex(): InitResult =
        io({ PythonBridge.callJson("rebuild_index") }, { json.decodeFromString(it) })

    // -- listing -------------------------------------------------------------

    suspend fun listRoasts(): List<RoastSummary> =
        io({ PythonBridge.callJson("list_roasts") }, { json.decodeFromString<RoastListResponse>(it).roasts })

    // -- profile -------------------------------------------------------------

    suspend fun getProfile(uuid: String): RoastProfile =
        io({ PythonBridge.callJson("get_profile", uuid) }, { json.decodeFromString(it) })

    // -- sensory record ------------------------------------------------------

    suspend fun getSensory(uuid: String): SensoryRecord? =
        io({ PythonBridge.callJsonOrNull("get_sensory", uuid) ?: "null" }) { raw ->
            if (raw == "null") null else json.decodeFromString<SensoryRecord>(raw)
        }

    suspend fun createSensory(uuid: String): SensoryRecord =
        io({ PythonBridge.callJson("create_sensory", uuid) }, { json.decodeFromString(it) })

    suspend fun updateSensory(uuid: String, body: SensoryUpdate): SensoryRecord =
        io({ PythonBridge.callJson("update_sensory", uuid, json.encodeToString(body)) }, { json.decodeFromString(it) })

    suspend fun deleteSensory(uuid: String): DeleteResult =
        io({ PythonBridge.callJson("delete_sensory", uuid) }, { json.decodeFromString(it) })

    // -- cuppings ------------------------------------------------------------

    suspend fun addCupping(uuid: String, cupping: Cupping): SensoryRecord =
        io({ PythonBridge.callJson("add_cupping", uuid, json.encodeToString(cupping)) }, { json.decodeFromString(it) })

    suspend fun editCupping(uuid: String, index: Int, changes: Cupping): SensoryRecord =
        io({ PythonBridge.callJson("edit_cupping", uuid, index, json.encodeToString(changes)) }, { json.decodeFromString(it) })

    suspend fun removeCupping(uuid: String, index: Int): SensoryRecord =
        io({ PythonBridge.callJson("remove_cupping", uuid, index) }, { json.decodeFromString(it) })

    // -- radar ---------------------------------------------------------------

    suspend fun updateRadar(uuid: String, values: List<Double>, labels: List<String>? = null): SensoryRecord =
        io({
            val labelsJson = labels?.let { json.encodeToString(it) } ?: "null"
            PythonBridge.callJson("update_radar", uuid, json.encodeToString(values), labelsJson)
        }, { json.decodeFromString(it) })

    suspend fun radarLabels(): List<String> =
        io({ PythonBridge.callJson("radar_labels") }, { json.decodeFromString<RadarLabelsResponse>(it).labels })

    // -- schema constants ----------------------------------------------------

    suspend fun scoreKeys(): List<String> =
        io({ PythonBridge.callJson("score_keys") }, { json.decodeFromString<KeysResponse>(it).keys })

    suspend fun defectKeys(): List<String> =
        io({ PythonBridge.callJson("defect_keys") }, { json.decodeFromString<KeysResponse>(it).keys })
}
