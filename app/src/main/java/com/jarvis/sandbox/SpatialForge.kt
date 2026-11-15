package com.jarvis.sandbox

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.RocketLaunch
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import kotlin.concurrent.thread

@Composable
fun SpatialForgeScreen(workerUrl: String, workerToken: String) {
    var goal by remember { mutableStateOf("Construct a Rem-inspired humanoid blockout") }
    var status by remember { mutableStateOf("Nano-Builder ready. Connect to the local Termux worker.") }
    var objects by remember { mutableStateOf(listOf<String>()) }
    var events by remember { mutableStateOf(listOf<String>()) }
    var busy by remember { mutableStateOf(false) }
    fun refresh() {
        busy = true
        thread {
            val r = runCatching { agentHttp(workerUrl, "/api/v1/spatial/scene", workerToken, "GET") }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                r.onSuccess { j ->
                    val scene = j.optJSONObject("scene")
                    val arr = scene?.optJSONArray("objects")
                    objects = (0 until (arr?.length() ?: 0)).mapNotNull { arr?.optJSONObject(it)?.optString("name") }
                    val ev = j.optJSONArray("recent_events")
                    events = (0 until (ev?.length() ?: 0)).mapNotNull { ev?.optJSONObject(it)?.let { x -> "${x.optString("worker")}: ${x.optString("detail")}" } }.takeLast(12).reversed()
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
                agentHttp(workerUrl, "/api/v1/spatial/nano-build", workerToken, "POST",
                    JSONObject().put("goal", goal))
            }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                r.onSuccess { j ->
                    val result = j.optJSONObject("result")
                    status = "Build complete • ${result?.optInt("created",0)} components created. This is an editable blockout, not finished anatomy."
                }.onFailure { status = "Build failed: ${it.message}" }
                refresh()
            }
        }
    }
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column(Modifier.weight(1f)) {
                Text("JARVIS SPATIAL FORGE", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("LOCAL NANO-BUILDER • EDITABLE SCENE", color = Color(0xFF55D6FF), fontSize = 10.sp)
            }
            IconButton(onClick = { refresh() }, enabled = !busy) { Icon(Icons.Default.Refresh, "Refresh") }
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
        Text("CONSTRUCTION COMPONENTS • ${objects.size}", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold)
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(objects) { name -> Text("▣  $name", color = Color.White, modifier = Modifier.fillMaxWidth().padding(7.dp)) }
            item { Text("WORKER ACTIVITY", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold) }
            items(events) { event -> Text("✦  $event", color = Color(0xFFB7C6D8), fontSize = 11.sp, modifier = Modifier.padding(5.dp)) }
        }
    }
}
