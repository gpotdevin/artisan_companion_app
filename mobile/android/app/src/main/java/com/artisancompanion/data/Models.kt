package com.artisancompanion.data

import kotlinx.serialization.Serializable

// ---------------------------------------------------------------------------
// Listing
// ---------------------------------------------------------------------------

@Serializable
data class RoastListResponse(val roasts: List<RoastSummary> = emptyList())

@Serializable
data class RoastSummary(
    val roast_uuid: String,
    val source_file: String? = null,
    val title: String? = null,
    val beans: String? = null,
    val roast_date: String? = null,
    val green_weight_g: Double? = null,
    val roasted_weight_g: Double? = null,
    val drop_bt_c: Double? = null,
    val fcs_time_s: Double? = null,
    val total_time_s: Double? = null,
    val parse_ok: Boolean = true,
    val error_msg: String? = null,
    val annotated: Boolean = false,
    val n_cuppings: Int = 0,
    val best_total: Double? = null,
    val last_cupping_date: String? = null,
)

@Serializable
data class InitResult(val ok: Boolean = true, val roast_count: Int = 0)

@Serializable
data class DeleteResult(val deleted: Boolean = false, val roast_uuid: String? = null)

@Serializable
data class RadarLabelsResponse(val labels: List<String> = emptyList())

@Serializable
data class KeysResponse(val keys: List<String> = emptyList())

// ---------------------------------------------------------------------------
// Profile viewer
// ---------------------------------------------------------------------------

@Serializable
data class RoastProfile(
    val roast_uuid: String,
    val source_file: String? = null,
    val title: String? = null,
    val beans: String? = null,
    val roast_date: String? = null,
    val green_weight_g: Double? = null,
    val roasted_weight_g: Double? = null,
    val drop_bt_c: Double? = null,
    val times_s: List<Double> = emptyList(),
    val bt_c: List<Double> = emptyList(),
    val et_c: List<Double> = emptyList(),
    val ror_c_per_min: List<Double?> = emptyList(),
    val markers: Map<String, Marker> = emptyMap(),
    val events: List<RoastEvent> = emptyList(),
    val phases: Phases = Phases(),
    val sensory: SensorySummary? = null,
    val background: BackgroundSeries? = null,
    val meta: ProfileMeta = ProfileMeta(),
)

@Serializable
data class Marker(
    val time_s: Double = 0.0,
    val temp_bt_c: Double? = null,
    val temp_et_c: Double? = null,
)

@Serializable
data class RoastEvent(
    val time_s: Double = 0.0,
    val index: Int = 0,
    val type_label: String? = null,
    val slider_value: Double? = null,
    val label: String? = null,
)

@Serializable
data class Phases(
    val drying_s: Double? = null,
    val maillard_s: Double? = null,
    val development_s: Double? = null,
    val total_s: Double? = null,
)

@Serializable
data class BackgroundSeries(
    val times_s: List<Double> = emptyList(),
    val bt_c: List<Double> = emptyList(),
)

@Serializable
data class ProfileMeta(
    val artisan_version: String? = null,
    val roastertype: String? = null,
    val ambient_temp_c: Double? = null,
    val sampling_interval_s: Double? = null,
)

@Serializable
data class SensorySummary(
    val cuppings: List<Cupping> = emptyList(),
    val radar: Radar = Radar(),
    val defects_observed: Map<String, Boolean> = emptyMap(),
    val best_total: Double? = null,
    val n_cuppings: Int = 0,
)

// ---------------------------------------------------------------------------
// Sensory record
// ---------------------------------------------------------------------------

@Serializable
data class SensoryRecord(
    val schema_version: Int = 1,
    val roast_uuid: String = "",
    val roast_ref: RoastRef = RoastRef(),
    val cuppings: List<Cupping> = emptyList(),
    val radar: Radar = Radar(),
    val defects_observed: Map<String, Boolean> = emptyMap(),
    val native_sync: NativeSync = NativeSync(),
    val media: List<MediaRef> = emptyList(),
)

@Serializable
data class RoastRef(val file: String? = null, val date: String? = null)

@Serializable
data class Radar(
    val labels: List<String> = emptyList(),
    val values: List<Double> = emptyList(),
)

@Serializable
data class NativeSync(val last_synced: String? = null, val fields: List<String> = emptyList())

@Serializable
data class MediaRef(val kind: String? = null, val path: String? = null)

@Serializable
data class Cupping(
    val date: String = "",
    val days_after_roast: Int? = null,
    val scores: Scores = Scores(),
    val descriptors: List<String> = emptyList(),
    val notes: String? = null,
)

@Serializable
data class Scores(
    val fragrance_aroma: Double? = null,
    val flavor: Double? = null,
    val aftertaste: Double? = null,
    val acidity: Double? = null,
    val body: Double? = null,
    val balance: Double? = null,
    val uniformity: Double? = null,
    val clean_cup: Double? = null,
    val sweetness: Double? = null,
    val overall: Double? = null,
    val defects: Double? = null,
    val total: Double? = null,
)

/** Body for update_sensory (matches store.update kwargs). */
@Serializable
data class SensoryUpdate(
    val roast_ref: RoastRef? = null,
    val radar: Radar? = null,
    val defects_observed: Map<String, Boolean>? = null,
    val media: List<MediaRef>? = null,
)
