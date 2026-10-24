package com.artisancompanion.ui.viewer

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.res.stringResource
import com.artisancompanion.R
import com.artisancompanion.data.RoastProfile
import com.artisancompanion.ui.theme.BtRed
import com.artisancompanion.ui.theme.ChartDimOverlay
import com.artisancompanion.ui.theme.CreamDim
import com.artisancompanion.ui.theme.EtBlue
import com.artisancompanion.ui.theme.MarkerWhite
import com.artisancompanion.ui.theme.PhaseDevelopment
import com.artisancompanion.ui.theme.PhaseDrying
import com.artisancompanion.ui.theme.PhaseMaillard
import com.artisancompanion.ui.theme.RorGrey
import android.graphics.Paint as AndroidPaint
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Artisan-style roast profile drawn on a Compose Canvas.
 *
 * Features (Milestone N3):
 * - BT (red, thick) / ET (blue) / RoR (grey, right axis) curves, each toggleable
 * - Time axis zeroed at CHARGE; pre-CHARGE region dimmed with a semi-transparent overlay
 * - Phase shading: Drying (CHARGE→DRY), Maillard (DRY→FCs), Development (FCs→DROP)
 * - Vertical marker lines: CHARGE, DRY, FCs, DROP, COOL (solid) + TP (dashed, derived)
 * - Event flags: small dots at the bottom of the chart at each event's time position
 * - Gridlines with temp (left) + time (bottom) + RoR (right) axes
 */
@Composable
fun ProfileChart(
    profile: RoastProfile,
    modifier: Modifier = Modifier,
    showBt: Boolean = true,
    showEt: Boolean = true,
    showRor: Boolean = true,
) {
    val times = profile.times_s
    val bt = profile.bt_c
    val et = profile.et_c
    val ror = profile.ror_c_per_min
    val markers = profile.markers
    val events = profile.events

    // Time zeroed at CHARGE
    val chargeTime = markers["CHARGE"]?.time_s
    val tOffset = chargeTime ?: 0.0
    val relTimes = if (times.isNotEmpty()) times.map { it - tOffset } else emptyList()

    // Display range includes 0 (CHARGE) and covers all data
    val rawTMin = relTimes.minOrNull() ?: 0.0
    val rawTMax = relTimes.maxOrNull() ?: 1.0
    val displayTMin = min(rawTMin, 0.0)
    val displayTMax = max(rawTMax, 1.0)
    val span = (displayTMax - displayTMin).coerceAtLeast(1.0)

    val tempMin = min(bt.minOrNull() ?: 0.0, et.minOrNull() ?: 0.0).coerceAtMost(20.0)
    val tempMax = max(bt.maxOrNull() ?: 0.0, et.maxOrNull() ?: 0.0).coerceAtLeast(230.0)
    val tempSpan = (tempMax - tempMin).coerceAtLeast(1.0)

    val rorPairs = relTimes.indices.mapNotNull { i ->
        ror.getOrNull(i)?.let { relTimes[i] to it }
    }
    val rorMax = (rorPairs.maxOfOrNull { it.second } ?: 30.0).coerceAtLeast(1.0)

    // TP: derived turning point at the BT minimum over post-CHARGE samples only
    // (relative time >= 0). Fallback only — the backend normally supplies markers["TP"].
    val tpIndex = if (bt.isNotEmpty()) {
        bt.indices
            .filter { i -> (relTimes.getOrNull(i) ?: Double.NEGATIVE_INFINITY) >= 0.0 }
            .minByOrNull { bt[it] }
    } else {
        null
    }
    val tpRelTime = tpIndex?.let { relTimes.getOrNull(it) }

    val axisPaint = AndroidPaint(AndroidPaint.ANTI_ALIAS_FLAG).apply {
        color = CreamDim.toArgb()
        textSize = 28f
    }
    val gridColor = CreamDim.copy(alpha = 0.2f)
    val dimOverlay = ChartDimOverlay
    val dashedEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 6f))

    // Axis + marker labels (hoisted: the Canvas draw lambda is not a @Composable context)
    val tempAxisLabel = stringResource(R.string.chart_axis_temp)
    val minAxisLabel = stringResource(R.string.chart_axis_min)
    val rorAxisLabel = stringResource(R.string.chart_axis_ror)
    val tpLabel = stringResource(R.string.chart_marker_tp)

    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val padL = 64f
        val padR = 64f
        val padT = 28f
        val padB = 48f
        val plotW = (w - padL - padR).coerceAtLeast(1f)
        val plotH = (h - padT - padB).coerceAtLeast(1f)

        fun x(t: Double) = padL + ((t - displayTMin) / span).toFloat() * plotW
        fun yTemp(v: Double) = padT + (1f - (v - tempMin) / tempSpan).toFloat() * plotH
        fun yRor(v: Double) = padT + (1f - (v / rorMax)).toFloat() * plotH

        // --- Phase shading (relative times) ---
        val dryRel = markers["DRY"]?.time_s?.let { it - tOffset }
        val fcsRel = markers["FCs"]?.time_s?.let { it - tOffset }
        val dropRel = markers["DROP"]?.time_s?.let { it - tOffset }
        // Drying: CHARGE(0) → DRY
        if (dryRel != null) {
            drawRect(PhaseDrying, Offset(x(0.0), padT), Size(x(dryRel) - x(0.0), plotH))
        }
        // Maillard: DRY → FCs
        if (dryRel != null && fcsRel != null) {
            drawRect(PhaseMaillard, Offset(x(dryRel), padT), Size(x(fcsRel) - x(dryRel), plotH))
        }
        // Development: FCs → DROP
        if (fcsRel != null && dropRel != null) {
            drawRect(PhaseDevelopment, Offset(x(fcsRel), padT), Size(x(dropRel) - x(fcsRel), plotH))
        }

        // --- Horizontal gridlines + temp labels (left axis), every 50 °C ---
        var tv = ceil(tempMin / 50.0) * 50.0
        while (tv <= tempMax) {
            val yy = yTemp(tv)
            drawLine(gridColor, Offset(padL, yy), Offset(padL + plotW, yy), strokeWidth = 1f)
            drawIntoCanvas {
                it.nativeCanvas.drawText("${tv.toInt()}\u00B0", 8f, yy + 8f, axisPaint)
            }
            tv += 50.0
        }

        // --- RoR right-axis labels, every 10 °C/min ---
        if (showRor) {
            var rv = 0.0
            while (rv <= rorMax) {
                val yy = yRor(rv)
                drawIntoCanvas {
                    it.nativeCanvas.drawText(
                        rv.toInt().toString(),
                        w - padR + 8f,
                        yy + 8f,
                        axisPaint,
                    )
                }
                rv += 10.0
            }
        }

        // --- Vertical gridlines + time labels (bottom axis), every 60 s (relative) ---
        var tt = ceil(displayTMin / 60.0) * 60.0
        while (tt <= displayTMax) {
            val xx = x(tt)
            drawLine(gridColor, Offset(xx, padT), Offset(xx, padT + plotH), strokeWidth = 1f)
            drawIntoCanvas {
                it.nativeCanvas.drawText(formatRelTime(tt), xx - 20f, h - 12f, axisPaint)
            }
            tt += 60.0
        }

        // --- Axis titles ---
        drawIntoCanvas { it.nativeCanvas.drawText(tempAxisLabel, 8f, padT - 4f, axisPaint) }
        drawIntoCanvas { it.nativeCanvas.drawText(minAxisLabel, w - padR + 8f, h - 12f, axisPaint) }
        if (showRor) {
            drawIntoCanvas {
                it.nativeCanvas.drawText(rorAxisLabel, w - padR + 8f, padT - 4f, axisPaint)
            }
        }

        // --- Curves ---
        if (showBt) drawPolyline(relTimes, bt, ::x, ::yTemp, BtRed, strokeWidth = 2.5f)
        if (showEt) drawPolyline(relTimes, et, ::x, ::yTemp, EtBlue, strokeWidth = 1.5f)
        if (showRor && rorPairs.isNotEmpty()) {
            val path = Path()
            rorPairs.forEachIndexed { i, (t, v) ->
                val px = x(t)
                val py = yRor(v)
                if (i == 0) path.moveTo(px, py) else path.lineTo(px, py)
            }
            drawPath(path, RorGrey, style = Stroke(1.5f), alpha = 1f)
        }

        // --- Marker lines + labels (relative times) ---
        markers.forEach { (name, m) ->
            val relT = m.time_s - tOffset
            val mx = x(relT)
            if (name == "TP") {
                drawLine(
                    MarkerWhite, Offset(mx, padT), Offset(mx, padT + plotH),
                    strokeWidth = 1.5f, alpha = 0.7f, pathEffect = dashedEffect,
                )
            } else {
                drawLine(
                    MarkerWhite, Offset(mx, padT), Offset(mx, padT + plotH),
                    strokeWidth = 1f, alpha = 0.5f,
                )
            }
            drawIntoCanvas {
                it.nativeCanvas.drawText(name, mx + 4f, padT + 20f, axisPaint)
            }
        }

        // --- TP derived marker (dashed line at BT minimum, if not already in markers) ---
        if (tpRelTime != null && !markers.containsKey("TP")) {
            val mx = x(tpRelTime)
            drawLine(
                MarkerWhite, Offset(mx, padT), Offset(mx, padT + plotH),
                strokeWidth = 1.5f, alpha = 0.7f, pathEffect = dashedEffect,
            )
            drawIntoCanvas {
                it.nativeCanvas.drawText(tpLabel, mx + 4f, padT + 20f, axisPaint)
            }
        }

        // --- Event flags: small dots at the bottom of the plot area ---
        val flagY = padT + plotH - 6f
        events.forEach { event ->
            val relT = event.time_s - tOffset
            val ex = x(relT)
            if (ex in padL..(padL + plotW)) {
                drawCircle(
                    color = CreamDim,
                    radius = 4f,
                    center = Offset(ex, flagY),
                    alpha = 0.8f,
                )
            }
        }

        // --- Pre-CHARGE dimming overlay, drawn LAST so curves, gridlines,
        //     markers and flags in the warm-up region all read as dimmed ---
        if (chargeTime != null && displayTMin < 0.0) {
            val chargeX = x(0.0)
            drawRect(dimOverlay, Offset(padL, padT), Size(chargeX - padL, plotH))
        }
    }
}

/** Format a relative time (seconds, may be negative) as M:SS or -M:SS. */
private fun formatRelTime(sec: Double): String {
    val total = sec.roundToInt()
    val sign = if (total < 0) "-" else ""
    val a = abs(total)
    return "$sign${a / 60}:${String.format("%02d", a % 60)}"
}

private fun DrawScope.drawPolyline(
    times: List<Double>,
    series: List<Double>,
    x: (Double) -> Float,
    y: (Double) -> Float,
    color: Color,
    strokeWidth: Float = 2.5f,
) {
    val n = min(times.size, series.size)
    if (n == 0) return
    val path = Path()
    for (i in 0 until n) {
        val px = x(times[i])
        val py = y(series[i])
        if (i == 0) path.moveTo(px, py) else path.lineTo(px, py)
    }
    drawPath(path, color, style = Stroke(strokeWidth))
}
