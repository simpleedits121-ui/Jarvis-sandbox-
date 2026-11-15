package com.jarvis.sandbox

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.RocketLaunch
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import kotlin.concurrent.thread

private data class SwarmAgentUi(val id: String, val name: String, val role: String, val objective: String)
private data class SwarmTaskUi(val id: String, val goal: String, val status: String, val subtasks: Int, val done: Int, val review: String)

@Composable
fun SwarmDashboard(workerUrl: String, workerToken: String) {
    var agents by remember { mutableStateOf<List<SwarmAgentUi>>(emptyList()) }
    var tasks by remember { mutableStateOf<List<SwarmTaskUi>>(emptyList()) }
    var goal by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Connect to the local Termux worker to load your team.") }
    var busy by remember { mutableStateOf(false) }
    var selectedTask by remember { mutableStateOf<SwarmTaskUi?>(null) }
    var taskDetail by remember { mutableStateOf("") }
    var forgeStatus by remember { mutableStateOf("Generate the v0.6 smooth-mesh anime character build locally.") }
    var forgeUrl by remember { mutableStateOf("") }
    val context = LocalContext.current

    fun refresh() {
        busy = true
        thread {
            val result = runCatching {
                val a = agentHttp(workerUrl, "/api/v1/swarm/agents", workerToken, "GET").optJSONArray("agents")
                val t = agentHttp(workerUrl, "/api/v1/swarm/tasks?limit=30", workerToken, "GET").optJSONArray("tasks")
                val aa = buildList { if (a != null) for (i in 0 until a.length()) { val x = a.optJSONObject(i) ?: continue; add(SwarmAgentUi(x.optString("agent_id"), x.optString("name"), x.optString("role"), x.optString("objective"))) } }
                val tt = buildList { if (t != null) for (i in 0 until t.length()) { val x = t.optJSONObject(i) ?: continue; val s = x.optJSONArray("subtasks"); var count = 0; var done = 0; if (s != null) for (j in 0 until s.length()) { count++; if (s.optJSONObject(j)?.optString("status") == "completed") done++ }; add(SwarmTaskUi(x.optString("task_id"), x.optString("goal"), x.optString("status"), count, done, x.optJSONObject("review")?.optString("note") ?: "")) } }
                aa to tt
            }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                result.onSuccess { (aa, tt) -> agents = aa; tasks = tt; status = "Worker connected • ${aa.size} agents • ${tt.size} tasks" }
                    .onFailure { status = "Worker connection failed: ${it.message}" }
                busy = false
            }
        }
    }

    fun createTask() {
        val text = goal.trim()
        if (text.length < 3 || busy) return
        busy = true
        thread {
            val result = runCatching { agentHttp(workerUrl, "/api/v1/swarm/tasks", workerToken, "POST", JSONObject().put("goal", text)) }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                result.onSuccess { status = "Task queued • ${it.optString("task_id").take(8)}"; goal = ""; refresh() }
                    .onFailure { status = "Could not create task: ${it.message}"; busy = false }
            }
        }
    }

    fun generateRem() {
        if (busy) return
        busy = true
        forgeStatus = "Generating character meshes locally…"
        thread {
            val result = runCatching { agentHttp(workerUrl, "/api/v1/character/generate", workerToken, "POST", JSONObject().put("character", "rem-inspired")) }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                result.onSuccess { json ->
                    val report = json.optJSONObject("report")
                    val files = json.optJSONArray("files")
                    var glbPath = ""
                    if (files != null) for (i in 0 until files.length()) {
                        val item = files.optJSONObject(i) ?: continue
                        if (item.optString("filename").endsWith(".glb")) glbPath = item.optString("download")
                    }
                    forgeUrl = glbPath
                    forgeStatus = "Generated ${report?.optInt("parts") ?: 0} mesh parts • ${report?.optInt("triangles") ?: 0} triangles. v0.6 smooth geometry • UV textures, rigging and animation are next."
                    status = "Character Forge generated a local GLB asset"
                }.onFailure { forgeStatus = "Generation failed: ${it.message}" }
                busy = false
                refresh()
            }
        }
    }

    fun runTask(task: SwarmTaskUi) {
        busy = true
        thread {
            val result = runCatching { agentHttp(workerUrl, "/api/v1/swarm/tasks/${task.id}/run", workerToken, "POST") }
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                result.onSuccess { json ->
                    val lines = mutableListOf<String>()
                    val subtasks = json.optJSONArray("subtasks")
                    if (subtasks != null) for (i in 0 until subtasks.length()) { val item = subtasks.optJSONObject(i) ?: continue; lines.add("${item.optString("agent_name")}: ${item.optString("status")}\n${item.optString("result")}") }
                    taskDetail = lines.joinToString("\n\n") + "\n\nSupervisor: " + (json.optJSONObject("review")?.optString("note") ?: "Review pending")
                    selectedTask = task
                    status = "Coordination run finished • review required"
                }.onFailure { status = "Run failed: ${it.message}" }
                busy = false
                refresh()
            }
        }
    }

    LaunchedEffect(workerUrl, workerToken) { refresh() }
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) {
                Text("JARVIS SWARM", fontSize = 21.sp, fontWeight = FontWeight.Bold)
                Text("Offline agent coordination • local worker", color = Color(0xFF91A4BC), fontSize = 11.sp)
            }
            IconButton(onClick = { refresh() }, enabled = !busy) { Icon(Icons.Default.Refresh, "Refresh") }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF14283B)), shape = RoundedCornerShape(14.dp)) {
            Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("LOCAL STATUS", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Text(status, color = Color.White, fontSize = 12.sp)
                Text("Swarm coordination works offline. Character Forge v0.6 creates smoother indexed meshes with layered eyes and curved hair. Neural reasoning, UV textures, rigging and animation are still pending.", color = Color(0xFFB7C6D8), fontSize = 10.sp)
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF14283B)), shape = RoundedCornerShape(14.dp)) {
            Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text("CHARACTER FORGE • FIRST REM-INSPIRED BUILD", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Text("Generate a smoother anime-style character mesh locally from scratch. No cloud model or paid API.", color = Color.White, fontSize = 12.sp)
                Text(forgeStatus, color = Color(0xFFB7C6D8), fontSize = 11.sp)
                Button(onClick = { generateRem() }, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.RocketLaunch, null); Spacer(Modifier.width(7.dp)); Text("Generate Rem Character")
                }
                if (forgeUrl.isNotBlank()) OutlinedButton(onClick = {
                    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(workerUrl.trimEnd('/') + forgeUrl))) }
                }, modifier = Modifier.fillMaxWidth()) { Text("Open / download GLB") }
            }
        }
        Text("AGENT TEAM  •  ${agents.size}", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(agents, key = { it.id }) { agent ->
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
                    Column(Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(agent.name, fontWeight = FontWeight.Bold, color = Color.White)
                        Text(agent.role.uppercase(), color = Color(0xFF55D6FF), fontSize = 9.sp)
                        Text(agent.objective, color = Color(0xFFB7C6D8), fontSize = 11.sp)
                    }
                }
            }
            item {
                Text("CREATE TASK", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp, modifier = Modifier.padding(top = 8.dp))
                OutlinedTextField(value = goal, onValueChange = { goal = it }, modifier = Modifier.fillMaxWidth(), label = { Text("What should the character team work on?") }, minLines = 2, maxLines = 4)
                Button(onClick = { createTask() }, enabled = !busy && goal.trim().length >= 3, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.RocketLaunch, null); Spacer(Modifier.width(7.dp)); Text("Create Swarm Task")
                }
                Text("TASK BOARD  •  ${tasks.size}", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp, modifier = Modifier.padding(top = 8.dp))
            }
            items(tasks, key = { it.id }) { task ->
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Text(task.goal, color = Color.White, fontWeight = FontWeight.SemiBold)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AssistChip(onClick = {}, label = { Text(task.status.uppercase()) })
                            Spacer(Modifier.width(8.dp)); Text("${task.done}/${task.subtasks} agents complete", color = Color(0xFF91A4BC), fontSize = 10.sp)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { runTask(task) }, enabled = !busy && task.status != "review", modifier = Modifier.weight(1f)) { Text("Run team") }
                            OutlinedButton(onClick = { selectedTask = task; taskDetail = task.review.ifBlank { "No review report yet." } }, modifier = Modifier.weight(1f)) { Text("Details") }
                        }
                    }
                }
            }
        }
        if (selectedTask != null) {
            AlertDialog(onDismissRequest = { selectedTask = null }, title = { Text("Swarm report") }, text = { Text(taskDetail.ifBlank { selectedTask?.review ?: "No report available." }) }, confirmButton = { TextButton(onClick = { selectedTask = null }) { Text("Close") } })
        }
    }
}
