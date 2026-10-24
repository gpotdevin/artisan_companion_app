package com.artisancompanion.ui.editor

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import com.artisancompanion.ui.theme.Caramel
import com.artisancompanion.ui.theme.CaramelBright
import com.artisancompanion.ui.theme.Cream
import com.artisancompanion.ui.theme.CreamDim
import android.graphics.Paint as AndroidPaint
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/** Flavor radar (spider) chart drawn on a Compose Canvas. Values are 0-10. */
@Composable
fun RadarChart(labels: List<String>, values: List<Double>, modifier: Modifier = Modifier) {
    val n = labels.size.coerceAtLeast(3)
    val maxV = 10.0

    val labelPaint = AndroidPaint(AndroidPaint.ANTI_ALIAS_FLAG).apply {
        color = Cream.toArgb()
        textSize = 26f
        textAlign = AndroidPaint.Align.CENTER
    }

    Canvas(modifier) {
        val cx = size.width / 2f
        val cy = size.height / 2f
        val radius = min(size.width, size.height) / 2f * 0.68f

        // Concentric rings (0..10 in 5 steps).
        for (ring in 1..5) {
            drawCircle(
                color = CreamDim.copy(alpha = 0.2f),
                radius = radius * ring / 5f,
                center = Offset(cx, cy),
                style = Stroke(1f),
            )
        }

        val angleStep = 2 * PI / n

        // Axes.
        for (i in 0 until n) {
            val angle = -PI / 2 + i * angleStep
            val ex = cx + (cos(angle) * radius).toFloat()
            val ey = cy + (sin(angle) * radius).toFloat()
            drawLine(CreamDim.copy(alpha = 0.3f), Offset(cx, cy), Offset(ex, ey), strokeWidth = 1f)
        }

        // Polygon.
        val points = (0 until n).map { i ->
            val angle = -PI / 2 + i * angleStep
            val v = (values.getOrNull(i) ?: 0.0).coerceIn(0.0, maxV) / maxV
            Offset(cx + (cos(angle) * radius * v).toFloat(), cy + (sin(angle) * radius * v).toFloat())
        }
        if (points.size >= 3) {
            val path = Path().apply {
                points.forEachIndexed { i, p -> if (i == 0) moveTo(p.x, p.y) else lineTo(p.x, p.y) }
                close()
            }
            drawPath(path, Caramel.copy(alpha = 0.25f))
            drawPath(path, Caramel, style = Stroke(2.5f))
            points.forEach { drawCircle(CaramelBright, 5f, it) }
        }

        // Labels.
        for (i in 0 until n) {
            val angle = -PI / 2 + i * angleStep
            val lx = cx + (cos(angle) * radius * 1.18).toFloat()
            val ly = cy + (sin(angle) * radius * 1.18).toFloat()
            drawIntoCanvas { it.nativeCanvas.drawText(labels.getOrNull(i) ?: "", lx, ly, labelPaint) }
        }
    }
}
