package com.artisancompanion.ui.viewer

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Stroke
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.toArgb
import com.artisancompanion.data.RoastProfile
import com.artisancompanion.ui.theme.BtRed
import com.artisancompanion.ui.theme.CreamDim
import com.artisancompanion.ui.theme.EtBlue
import com.artisancompanion.ui.theme.MarkerWhite
import com.artisancompanion.ui.theme.PhaseDevelopment
import com.artisancompanion.ui.theme.PhaseDrying
import com.artisancompanion.ui.theme.PhaseMaillard
import com.artisancompanion.ui.theme.RorGrey
import android.graphics.Paint as AndroidPaint
import kotlin.math.ceil

/**
 * Artisan-style roast profile drawn on a Compose Canvas: BT/ET/RoR curves,
 * phase shading (Drying/Maillard/Development), gridlines with temp + time
 * axes, and marker lines (CHARGE/DRY/FCs/DROP/COOL/TP).
 */
@Composable
fun ProfileChart(profile: RoastProfile, modifier: Modifier = Modifier) {
    val times = profile.times_s
    val bt = profile.bt_c
    val et = profile.et_c
    val ror = profile.ror_c_per_min
    val markers = profile.markers

    val tMin = times.minOrNull() ?: 0.0
    val tMax = times.maxOrNull() ?: 1.0
    val span = (tMax - tMin).coerceAtLeast(1.0)
    val tempMin = minOf(bt.minOrNull() ?: 0.0, et.minOrNull() ?: 0.0).coerceAtMost(20.0)
    val tempMax = maxOf(bt.maxOrNull() ?: 0.0, et.maxOrNull() ?: 0.0).coerceAtLeast(230.0)
    val tempSpan = (tempMax - tempMin).coerceAtLeast(1.0)
    val rorPairs = times.indices.mapNotNull { i -> ror.getOrNull(i)?.let { times[i] to it } }
    val rorMax = (rorPairs.maxOfOrNull { it.second } ?: 30.0).coerceAtLeast(1.0)

    val axisPaint = AndroidPaint(AndroidPaint.ANTI_ALIAS_FLAG).apply {
        color = CreamDim.toArgb()
        textSize = 28f
    }
    val gridColor = CreamDim.copy(alpha = 0.25f)

    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val padL = 64f
        val padR = 64f
        val padT = 24f
        val padB = 48f
        val plotW = (w - padL - padR).coerceAtLeast(1f)
        val plotH = (h - padT - padB).coerceAtLeast(1f)

        fun x(t: Double) = padL + ((t - tMin) / span).toFloat() * plotW
        fun yTemp(v: Double) = padT + (1f - (v - tempMin) / tempSpan).toFloat() * plotH
        fun yRor(v: Double) = padT + (1f - (v / rorMax)).toFloat() * plotH

        // Phase shading: Drying = CHARGE->DRY, Maillard = DRY->FCs, Dev = FCs->DROP
        val charge = markers["CHARGE"]?.time_s
        val dry = markers["DRY"]?.time_s
        val fcs = markers["FCs"]?.time_s
        val drop = markers["DROP"]?.time_s
        if (charge != null && dry != null) {
            drawRect(PhaseDrying, Offset(x(charge), padT), Size(x(dry) - x(charge), plotH))
        }
        if (dry != null && fcs != null) {
            drawRect(PhaseMaillard, Offset(x(dry), padT), Size(x(fcs) - x(dry), plotH))
        }
        if (fcs != null && drop != null) {
            drawRect(PhaseDevelopment, Offset(x(fcs), padT), Size(x(drop) - x(fcs), plotH))
        }

        // Horizontal gridlines + temp labels (left axis), every 50 C
        var tv = ceil(tempMin / 50.0) * 50.0
        while (tv <= tempMax) {
            val yy = yTemp(tv)
            drawLine(gridColor, Offset(padL, yy), Offset(padL + plotW, yy), strokeWidth = 1f)
            drawIntoCanvas { it.nativeCanvas.drawText("${tv.toInt()} C", 8f, yy + 8f, axisPaint) }
            tv += 50.0
        }

        // Vertical gridlines + time labels (bottom axis), every 60 s
        var tt = ceil(tMin / 60.0) * 60.0
        while (tt <= tMax) {
            val xx = x(tt)
            drawLine(gridColor, Offset(xx, padT), Offset(xx, padT + plotH), strokeWidth = 1f)
            val m = (tt / 60).toInt()
            val s = (tt % 60).toInt()
            drawIntoCanvas {
                it.nativeCanvas.drawText(String.format("%d:%02d", m, s), xx - 20f, h - 12f, axisPaint)
            }
            tt += 60.0
        }

        drawIntoCanvas { it.nativeCanvas.drawText("Temp", 8f, padT - 4f, axisPaint) }
        drawIntoCanvas { it.nativeCanvas.drawText("min", w - padR + 8f, h - 12f, axisPaint) }

        // Curves
        drawPolyline(times, bt, ::x, ::yTemp, BtRed)
        drawPolyline(times, et, ::x, ::yTemp, EtBlue)
        if (rorPairs.isNotEmpty()) {
            val path = Path()
            rorPairs.forEachIndexed { i, (t, v) ->
                val px = x(t)
                val py = yRor(v)
                if (i == 0) path.moveTo(px, py) else path.lineTo(px, py)
            }
            drawPath(path, RorGrey, style = Stroke(1.5f), alpha = 0.9f)
        }

        // Marker lines + labels
        markers.forEach { (name, m) ->
            val mx = x(m.time_s)
            drawLine(MarkerWhite, Offset(mx, padT), Offset(mx, padT + plotH), strokeWidth = 1f, alpha = 0.6f)
            drawIntoCanvas { it.nativeCanvas.drawText(name, mx + 4f, padT + 20f, axisPaint) }
        }
    }
}

private fun DrawScope.drawPolyline(
    times: List<Double>,
    series: List<Double>,
    x: (Double) -> Float,
    y: (Double) -> Float,
    color: Color,
) {
    val n = minOf(times.size, series.size)
    if (n == 0) return
    val path = Path()
    for (i in 0 until n) {
        val px = x(times[i])
        val py = y(series[i])
        if (i == 0) path.moveTo(px, py) else path.lineTo(px, py)
    }
    drawPath(path, color, style = Stroke(2.5f))
}
