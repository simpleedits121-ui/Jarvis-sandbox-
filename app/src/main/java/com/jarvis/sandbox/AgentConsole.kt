package com.jarvis.sandbox

import android.os.Handler
import android.os.Looper
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

private data class AgentChatLine(val role: String, val content: String)
private data class AgentApproval(val id: String, val action: String, val reason: String)

@Composable
fun AgentScreen(workerUrl: String, workerToken: String) {
    val mainHandler = remember { Handler(Looper.getMainLooper()) }
    var localBase by remember { mutableStateOf("http://127.0.0.1:8080/v1") }
    var localModel by remember { mutableStateOf("") }
    var remoteBase by remember { mutableStateOf("https://api.openai.com/v1") }
    var remoteModel by remember { mutableStateOf("gpt-4o-mini") }
    var remoteKey by remember { mutableStateOf("") }
    var keyAlreadySet by remember { mutableStateOf(false) }
    var configOpen by remember { mutableStateOf(true) }
    var configStatus by remember { mutableStateOf("Worker not checked. Start the Termux worker first.") }
    var busy by remember { mutableStateOf(false) }
    var input by remember { mutableStateOf("") }
    var provider by remember { mutableStateOf("No model selected") }
    var trace by remember { mutableStateOf("Local-first routing: local GGUF endpoint → remote API fallback → deterministic CPU workers.") }
    val messages = remember { mutableStateListOf<AgentChatLine>() }
    val approvals = remember { mutableStateListOf<AgentApproval>() }

    fun refreshApprovals() {
        val base = workerUrl
        val token = workerToken
        thread {
            val result = runCatching {
                agentHttp(base, "/api/v1/agent/approvals", token, "GET")
            }
            mainHandler.post {
                approvals.clear()
                result.getOrNull()?.optJSONArray("approvals")?.let { array ->
                    for (i in 0 until array.length()) {
                        val item = array.optJSONObject(i) ?: continue
                        approvals.add(AgentApproval(item.optString("approval_id"), item.optString("action"), item.optString("reason")))
                    }
                }
            }
        }
    }

    fun loadConfig() {
        busy = true
        val base = workerUrl
        val token = workerToken
        thread {
            val result = runCatching { agentHttp(base, "/api/v1/agent/config", token, "GET") }
            mainHandler.post {
                result.onSuccess { json ->
                    localBase = json.optString("local_base_url", localBase)
                    localModel = json.optString("local_model", localModel)
                    remoteBase = json.optString("remote_base_url", remoteBase)
                    remoteModel = json.optString("remote_model", remoteModel)
                    keyAlreadySet = json.optBoolean("remote_key_set", false)
                    configStatus = "Connected to worker • ${json.optString("strategy", "local-first fallback")}" 
                }.onFailure { configStatus = "Worker unavailable: ${it.message}" }
                busy = false
            }
            refreshApprovals()
        }
    }

    fun saveConfig() {
        busy = true
        val base = workerUrl
        val token = workerToken
        val localUrl = localBase
        val localId = localModel
        val remoteUrl = remoteBase
        val remoteId = remoteModel
        val secret = remoteKey
        thread {
            val body = JSONObject()
                .put("local_base_url", localUrl)
                .put("local_model", localId)
                .put("remote_base_url", remoteUrl)
                .put("remote_model", remoteId)
            if (secret.isNotBlank()) body.put("remote_api_key", secret)
            val result = runCatching { agentHttp(base, "/api/v1/agent/config", token, "POST", body) }
            mainHandler.post {
                result.onSuccess { json ->
                    keyAlreadySet = json.optBoolean("remote_key_set", false)
                    remoteKey = ""
                    configStatus = "Saved securely in the local Termux worker • local-first, remote fallback"
                }.onFailure { configStatus = "Save failed: ${it.message}" }
                busy = false
            }
        }
    }

    fun sendMessage() {
        val prompt = input.trim()
        if (prompt.isEmpty() || busy) return
        messages.add(AgentChatLine("user", prompt))
        input = ""
        busy = true
        val base = workerUrl
        val token = workerToken
        val history = JSONArray()
        messages.dropLast(1).takeLast(12).forEach { line ->
            history.put(JSONObject().put("role", line.role).put("content", line.content))
        }
        thread {
            val body = JSONObject().put("message", prompt).put("history", history)
            val result = runCatching { agentHttp(base, "/api/v1/agent/chat", token, "POST", body) }
            mainHandler.post {
                result.onSuccess { json ->
                    val reply = json.optString("reply", "Task completed.")
                    provider = json.optString("provider", "worker")
                    val actions = json.optJSONArray("actions")
                    val actionLines = mutableListOf<String>()
                    if (actions != null) {
                        for (i in 0 until actions.length()) {
                            val action = actions.optJSONObject(i) ?: continue
                            actionLines.add(action.optString("result", action.toString()))
                            val pending = action.optJSONObject("pending_approval")
                            if (pending != null) approvals.add(
                                AgentApproval(pending.optString("approval_id"), pending.optString("action"), pending.optString("reason"))
                            )
                        }
                    }
                    val fallbackErrors = json.optJSONArray("fallback_errors")
                    val traceArray = json.optJSONArray("worker_trace")
                    trace = buildString {
                        if (traceArray != null) for (i in 0 until traceArray.length()) append("• ").append(traceArray.optString(i)).append('\n')
                        if (fallbackErrors != null && fallbackErrors.length() > 0) {
                            append("Provider fallback details:\n")
                            for (i in 0 until fallbackErrors.length()) append("• ").append(fallbackErrors.optString(i)).append('\n')
                        }
                    }.ifBlank { "Task routed through $provider." }
                    messages.add(AgentChatLine("assistant", reply + if (actionLines.isNotEmpty()) "\n\nWorker results:\n" + actionLines.joinToString("\n") else ""))
                    refreshApprovals()
                }.onFailure {
                    messages.add(AgentChatLine("assistant", "I couldn't reach the local worker: ${it.message}. Start worker/run_termux.sh in Termux and retry."))
                }
                busy = false
            }
        }
    }

    fun decideApproval(id: String, approved: Boolean) {
        busy = true
        val base = workerUrl
        val token = workerToken
        thread {
            val body = JSONObject().put("approved", approved)
            val result = runCatching { agentHttp(base, "/api/v1/agent/approvals/$id", token, "POST", body) }
            mainHandler.post {
                result.onSuccess { json ->
                    messages.add(AgentChatLine("assistant", json.optString("result", if (approved) "Approved." else "Rejected.")))
                    approvals.removeAll { it.id == id }
                }.onFailure { configStatus = "Approval action failed: ${it.message}" }
                busy = false
                refreshApprovals()
            }
        }
    }

    LaunchedEffect(workerUrl, workerToken) { loadConfig() }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("JARVIS SWARM", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("AI Director • Local workers • Approval-controlled tools", color = Color(0xFF91A4BC), fontSize = 12.sp)
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF14283B)), shape = RoundedCornerShape(14.dp)) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Bolt, tint = Color(0xFF55D6FF), contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("LOCAL-FIRST ROUTER", fontWeight = FontWeight.Bold, color = Color(0xFF55D6FF))
                }
                Text("1. Local GGUF model  →  2. Remote model fallback  →  3. Built-in CPU workers", color = Color(0xFFD3E3F0), fontSize = 12.sp)
                Text(configStatus, color = Color(0xFFB7C6D8), fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { loadConfig() }, enabled = !busy) {
                        Icon(Icons.Default.Refresh, null); Text(" Refresh")
                    }
                    TextButton(onClick = { configOpen = !configOpen }) { Text(if (configOpen) "Hide settings" else "Model settings") }
                }
            }
        }

        if (configOpen) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("LOCAL MODEL (GGUF SERVER)", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                    OutlinedTextField(localBase, { localBase = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Local OpenAI-compatible URL") }, singleLine = true)
                    OutlinedTextField(localModel, { localModel = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Local model ID") }, supportingText = { Text("Example: the model name reported by your llama.cpp server") }, singleLine = true)
                    Divider(color = Color(0xFF26384B))
                    Text("REMOTE FALLBACK (OPTIONAL)", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                    OutlinedTextField(remoteBase, { remoteBase = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Remote OpenAI-compatible URL") }, singleLine = true)
                    OutlinedTextField(remoteModel, { remoteModel = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Remote model ID") }, singleLine = true)
                    OutlinedTextField(remoteKey, { remoteKey = it }, modifier = Modifier.fillMaxWidth(), label = { Text(if (keyAlreadySet) "API key (saved; enter to replace)" else "Remote API key") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
                    Text("The key is stored only in the local Termux worker settings file with owner-only permissions. Do not expose the worker to the internet.", color = Color(0xFF91A4BC), fontSize = 10.sp)
                    Button(onClick = { saveConfig() }, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("Save model connections") }
                }
            }
        }

        Text("DIRECTOR CHAT", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 11.sp)
        if (messages.isEmpty()) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Give JARVIS a task", fontWeight = FontWeight.Bold)
                    Text("Try: Create a small anime laboratory scene with a desk, chair, monitor, plant and cinematic camera movement.", color = Color(0xFFB7C6D8), fontSize = 12.sp)
                    Text("The first local worker build creates an OBJ preview and a Blender Python scene script. It does not yet reconstruct a real person from a selfie.", color = Color(0xFF91A4BC), fontSize = 11.sp)
                }
            }
        }
        messages.forEach { line ->
            Card(colors = CardDefaults.cardColors(containerColor = if (line.role == "user") Color(0xFF183149) else Color(0xFF111B2B))) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(if (line.role == "user") "YOU" else "JARVIS • $provider", color = Color(0xFF55D6FF), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Text(line.content, color = Color.White, fontSize = 13.sp)
                }
            }
        }
        OutlinedTextField(input, { input = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Tell JARVIS what to build or do") }, minLines = 2, maxLines = 5)
        Button(onClick = { sendMessage() }, enabled = !busy && input.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
            if (busy) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Icon(Icons.Default.Send, null)
            Spacer(Modifier.width(8.dp)); Text("Send to JARVIS Director")
        }
        if (trace.isNotBlank()) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF09121D))) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("WORKER TRACE", color = Color(0xFF55D6FF), fontWeight = FontWeight.Bold, fontSize = 10.sp)
                    Text(trace, color = Color(0xFFB7F6D2), fontSize = 11.sp)
                }
            }
        }
        if (approvals.isNotEmpty()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Security, tint = Color(0xFFFFC66D), contentDescription = null)
                Spacer(Modifier.width(7.dp))
                Text("DESTRUCTIVE ACTION APPROVALS", color = Color(0xFFFFC66D), fontWeight = FontWeight.Bold, fontSize = 11.sp)
            }
            approvals.forEach { approval ->
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF2B2116))) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(approval.action, fontWeight = FontWeight.Bold)
                        Text(approval.reason, color = Color(0xFFE5D6C2), fontSize = 12.sp)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { decideApproval(approval.id, true) }, enabled = !busy) {
                                Icon(Icons.Default.CheckCircle, null); Text(" Approve")
                            }
                            OutlinedButton(onClick = { decideApproval(approval.id, false) }, enabled = !busy) { Text("Reject") }
                        }
                    }
                }
            }
        }
        Text("Safety: no unrestricted shell. File deletion, overwrites and Blender script execution require explicit approval.", color = Color(0xFF91A4BC), fontSize = 10.sp)
    }
}

private fun agentHttp(
    baseUrl: String,
    path: String,
    token: String,
    method: String,
    body: JSONObject? = null
): JSONObject {
    val base = baseUrl.trim().trimEnd('/')
    val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
        requestMethod = method
        connectTimeout = 8000
        readTimeout = 90000
        setRequestProperty("Accept", "application/json")
        if (token.isNotBlank()) setRequestProperty("Authorization", "Bearer $token")
        if (body != null) {
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
        }
    }
    if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
    val code = connection.responseCode
    val stream = if (code in 200..299) connection.inputStream else connection.errorStream
    val text = stream?.bufferedReader()?.use { it.readText() } ?: "{}"
    connection.disconnect()
    if (code !in 200..299) throw IllegalStateException("HTTP $code: $text")
    return JSONObject(text)
}
