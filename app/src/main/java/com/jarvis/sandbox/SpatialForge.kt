package com.jarvis.sandbox

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.RocketLaunch
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import kotlin.concurrent.thread
import kotlin.math.cos
import kotlin.math.sin

private data class ForgePart(
    val id: String,
    val name: String,
    val type: String,
    val x: Float, val y: Float, val z: Float,
    val sx: Float, val sy: Float, val sz: Float,
    val region: String
)

@Composable
fun SpatialForgeScreen(workerUrl: String, workerToken: String) {
    var goal by remember { mutableStateOf("Construct a Rem-inspired humanoid blockout") }
    var status by remember { mutableStateOf("Nano-Builder ready. Connect to the local Termux worker.") }
    var objects by remember { mutableStateOf(listOf<ForgePart>()) }
    var events by remember { mutableStateOf(listOf<String>()) }
    var busy by remember { mutableStateOf(false) }
    var yaw by remember { mutableFloatStateOf(-0.55f) }
    var pitch by remember { mutableFloatStateOf(0.12f) }
    var zoom by remember { mutableFloatStateOf(1f) }

    fun refresh() {
        busy = true
        thread {
            val r = runCatching { agentHttp(workerUrl, "/api/v1/spatial/scene", workerToken, "GET") }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                r.onSuccess { j ->
                    val scene = j.optJSONObject("scene")
                    val arr = scene?.optJSONArray("objects")
                    objects = (0 until (arr?.length() ?: 0)).mapNotNull { i ->
                        val o = arr?.optJSONObject(i) ?: return@mapNotNull null
                        val tr = o.optJSONObject("transform")
                        val pos = tr?.optJSONArray("position")
                        val scale = o.optJSONArray("scale")
                        ForgePart(
                            id = o.optString("id"), name = o.optString("name"), type = o.optString("type", "cube"),
                            x = (pos?.optDouble(0) ?: 0.0).toFloat(),
                            y = (pos?.optDouble(1) ?: 0.0).toFloat(),
                            z = (pos?.optDouble(2) ?: 0.0).toFloat(),
                            sx = (scale?.optDouble(0) ?: 0.3).toFloat().coerceAtLeast(0.02f),
                            sy = (scale?.optDouble(1) ?: 0.3).toFloat().coerceAtLeast(0.02f),
                            sz = (scale?.optDouble(2) ?: 0.3).toFloat().coerceAtLeast(0.02f),
                            region = o.optString("region", "general")
                        )
                    }
                    val ev = j.optJSONArray("recent_events")
                    events = (0 until (ev?.length() ?: 0)).mapNotNull { i ->
                        ev?.optJSONObject(i)?.let { "${it.optString("worker")}: ${it.optString("detail")}" }
                    }.takeLast(12).reversed()
                    status = "Local scene loaded • ${objects.size} editable components"
                }.onFailure { status = "Worker unavailable: ${it.message}" }
                busy = false
            }
        }
    }

    fun build() {
        busy = true
        status = "Construction workers are building..."
        thread {
            val r = runCatching {
                agentHttp(workerUrl, "/api/v1/spatial/nano-build", workerToken, "POST", JSONObject().put("goal", goal))
            }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                r.onSuccess { j ->
                    val result = j.optJSONObject("result")
                    status = "Build complete • ${result?.optInt("created", 0)} components created."
                    yaw = -0.55f; pitch = 0.12f; zoom = 1f
                }.onFailure { status = "Build failed: ${it.message}" }
                refresh()
            }
        }
    }

    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column(Modifier.weight(1f)) {
                Text("JARVIS SPATIAL FORGE", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("3D BLOCKOUT VIEWPORT • LOCAL WORKERS", color = Color(0xFF55D6FF), fontSize = 10.sp)
            }
            IconButton(onClick = { refresh() }, enabled = !busy) { Icon(Icons.Default.Refresh, "Refresh scene") }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF102438)), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text("LIVE 3D SCENE", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold)
                ForgeViewport(objects = objects, yaw = yaw, pitch = pitch, zoom = zoom,
                    onGesture = { dx, dy, scale ->
                        yaw += dx * 0.008f
                        pitch = (pitch + dy * 0.006f).coerceIn(-1.15f, 1.15f)
                        zoom = (zoom * scale).coerceIn(0.45f, 2.8f)
                    }, modifier = Modifier.fillMaxWidth().height(270.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Drag to orbit • Pinch to zoom", color = Color(0xFFB7C6D8), fontSize = 11.sp)
                    Text("${objects.size} parts", color = Color(0xFF55D6FF), fontSize = 11.sp)
                }
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF14283B))) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("BOSS ORDER", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold)
                OutlinedTextField(value = goal, onValueChange = { goal = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Construction objective") })
                Button(onClick = { build() }, enabled = !busy && goal.length >= 3, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.RocketLaunch, null); Spacer(Modifier.width(7.dp)); Text("Start Nano-Construction")
                }
                Text(status, color = Color.White, fontSize = 12.sp)
            }
        }
        Text("SCENE COMPONENTS • ${objects.size}", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold)
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            items(objects, key = { it.id }) { part ->
                Text("▣  ${part.name}  ·  ${part.type}", color = Color.White, modifier = Modifier.fillMaxWidth().padding(horizontal = 7.dp, vertical = 5.dp), fontSize = 13.sp)
            }
            if (events.isNotEmpty()) item { Text("WORKER ACTIVITY", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold) }
            items(events) { event -> Text("✦  $event", color = Color(0xFFB7C6D8), fontSize = 11.sp, modifier = Modifier.padding(5.dp)) }
        }
    }
}

@Composable
private fun ForgeViewport(
    objects: List<ForgePart>, yaw: Float, pitch: Float, zoom: Float,
    onGesture: (Float, Float, Float) -> Unit, modifier: Modifier = Modifier
) {
    Canvas(modifier.pointerInput(Unit) {
        detectTransformGestures { _, pan, gestureZoom, _ -> onGesture(pan.x, pan.y, gestureZoom) }
    }) {
        drawRect(Color(0xFF071321))
        val cx = size.width / 2f
        val cy = size.height * 0.53f
        val unit = (size.height / 3.8f) * zoom
        fun project(x0: Float, y0: Float, z0: Float): Pair<Offset, Float> {
            val x = x0 * cos(yaw) - z0 * sin(yaw)
            val z = x0 * sin(yaw) + z0 * cos(yaw)
            val y = y0 * cos(pitch) - z * sin(pitch)
            val depth = y0 * sin(pitch) + z * cos(pitch)
            val perspective = (4.8f / (4.8f + depth * 0.12f)).coerceIn(0.72f, 1.3f)
            return Offset(cx + x * unit * perspective, cy - y * unit * perspective) to depth
        }
        // Subtle floor grid gives the blockout a stable spatial reference.
        for (i in -5..5) {
            val a = project(i * 0.25f, 0f, -1.25f).first
            val b = project(i * 0.25f, 0f, 1.25f).first
            val c = project(-1.25f, 0f, i * 0.25f).first
            val d = project(1.25f, 0f, i * 0.25f).first
            drawLine(Color(0x223D6B88), a, b, 1f)
            drawLine(Color(0x223D6B88), c, d, 1f)
        }
        data class Face(val points: List<Offset>, val depth: Float, val color: Color)
        val faces = mutableListOf<Face>()
        val local = listOf(
            floatArrayOf(-1f,-1f,-1f), floatArrayOf(1f,-1f,-1f), floatArrayOf(1f,1f,-1f), floatArrayOf(-1f,1f,-1f),
            floatArrayOf(-1f,-1f,1f), floatArrayOf(1f,-1f,1f), floatArrayOf(1f,1f,1f), floatArrayOf(-1f,1f,1f)
        )
        val quads = listOf(listOf(0,1,2,3), listOf(4,7,6,5), listOf(0,4,5,1), listOf(1,5,6,2), listOf(2,6,7,3), listOf(4,0,3,7))
        objects.forEach { part ->
            val color = when (part.region.lowercase()) {
                "head", "face_detail" -> Color(0xFFFFC5A8)
                "limb" -> Color(0xFF7BB7D8)
                else -> Color(0xFF55D6FF)
            }
            val pts = local.map { v -> project(part.x + v[0] * part.sx, part.y + v[1] * part.sy, part.z + v[2] * part.sz) }
            quads.forEachIndexed { index, q ->
                val p = q.map { pts[it].first }
                val depth = q.map { pts[it].second }.average().toFloat()
                val shade = when (index) { 0, 1 -> 0.72f; 2, 3 -> 1f; else -> 0.84f }
                faces += Face(p, depth, Color(color.red * shade, color.green * shade, color.blue * shade, 0.94f))
            }
        }
        faces.sortedBy { it.depth }.forEach { face ->
            val path = Path().apply {
                moveTo(face.points.first().x, face.points.first().y)
                face.points.drop(1).forEach { lineTo(it.x, it.y) }
                close()
            }
            drawPath(path, face.color)
            drawPath(path, Color(0xFF071321), style = Stroke(width = 1.1f))
        }
        if (objects.isEmpty()) {
            drawCircle(Color(0xFF55D6FF), radius = 5f, center = Offset(cx, cy))
        }
    }
}
