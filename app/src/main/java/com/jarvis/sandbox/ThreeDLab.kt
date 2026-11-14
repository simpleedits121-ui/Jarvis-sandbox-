package com.jarvis.sandbox

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Polymer
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

@Composable
fun ThreeDLabScreen(
    workerUrl: String,
    onWorkerUrlChange: (String) -> Unit,
    workerToken: String,
    onWorkerTokenChange: (String) -> Unit,
    imageName: String?,
    connectionStatus: String,
    jobStatus: String,
    hasJob: Boolean,
    hasOutput: Boolean,
    onChooseImage: () -> Unit,
    onCheckWorker: () -> Unit,
    onGenerate: () -> Unit,
    onCheckJob: () -> Unit,
    onDownloadOutput: () -> Unit
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("IMAGE → 3D WORKSHOP", color = Color(0xFF55D6FF), fontSize = 12.sp)
        Text("Turn a reference into a 3D asset", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Upload a character or object image. The worker sends it to a configured image-to-3D model provider and returns a job that can produce GLB/OBJ assets.",
            color = Color(0xFF91A4BC)
        )
        OutlinedTextField(
            value = workerUrl,
            onValueChange = onWorkerUrlChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Worker URL") },
            supportingText = { Text("Same-phone Termux default: http://127.0.0.1:8765") },
            singleLine = true
        )
        OutlinedTextField(
            value = workerToken,
            onValueChange = onWorkerTokenChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Worker access token (PC/LAN only)") },
            singleLine = true
        )
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row {
                    Icon(Icons.Default.Cloud, contentDescription = null, tint = Color(0xFF55D6FF))
                    Spacer(Modifier.width(8.dp))
                    Text("Worker connection", style = MaterialTheme.typography.titleMedium)
                }
                Text(connectionStatus, color = Color(0xFFB7C6D8))
                OutlinedButton(onClick = onCheckWorker, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Refresh, contentDescription = null)
                    Text("  Test worker")
                }
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF111B2B))) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row {
                    Icon(Icons.Default.Polymer, contentDescription = null, tint = Color(0xFF55D6FF))
                    Spacer(Modifier.width(8.dp))
                    Text("3D generation input", style = MaterialTheme.typography.titleMedium)
                }
                Text(imageName ?: "No image selected", color = Color(0xFF91A4BC))
                Button(onClick = onChooseImage, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Image, contentDescription = null)
                    Text("  Choose reference image")
                }
                Button(onClick = onGenerate, enabled = imageName != null, modifier = Modifier.fillMaxWidth()) {
                    Text("Generate 3D asset")
                }
                Text(jobStatus, color = Color(0xFFB7C6D8), fontSize = 12.sp)
                if (hasJob) {
                    OutlinedButton(onClick = onCheckJob, modifier = Modifier.fillMaxWidth()) {
                        Text("Check generation status")
                    }
                }
                if (hasOutput) {
                    Button(onClick = onDownloadOutput, modifier = Modifier.fillMaxWidth()) {
                        Text("Save generated GLB to workspace")
                    }
                }
            }
        }
        Text(
            "Reality check: one image cannot reveal hidden sides. The 3D model provider estimates unseen geometry. For production-quality characters, use multiple views when supported, then inspect topology, materials and rigging in Blender.",
            color = Color(0xFF91A4BC),
            fontSize = 12.sp
        )
    }
}

fun checkWorker(urlText: String, callback: (String) -> Unit) {
    thread {
        val result = runCatching {
            val base = urlText.trim().trimEnd('/')
            val conn = URL("$base/health").openConnection() as HttpURLConnection
            conn.connectTimeout = 4000
            conn.readTimeout = 4000
            conn.requestMethod = "GET"
            val body = conn.inputStream.bufferedReader().use { it.readText() }
            conn.disconnect()
            "Connected: $body"
        }.getOrElse { "Worker unavailable: ${it.message}" }
        callback(result)
    }
}

fun submitImageTo3d(
    resolver: ContentResolver,
    uri: Uri,
    urlText: String,
    token: String,
    callback: (String) -> Unit
) {
    thread {
        val result = runCatching {
            val base = urlText.trim().trimEnd('/')
            val name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) it.getString(0) else null
            } ?: "reference-image"
            val mime = resolver.getType(uri) ?: "application/octet-stream"
            val boundary = "JarvisBoundary${System.currentTimeMillis()}"
            val conn = URL("$base/api/v1/3d/jobs").openConnection() as HttpURLConnection
            conn.connectTimeout = 15000
            conn.readTimeout = 30000
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            if (token.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer $token")
            DataOutputStream(conn.outputStream).use { out ->
                out.writeBytes("--$boundary\r\n")
                out.writeBytes("Content-Disposition: form-data; name=\"image\"; filename=\"$name\"\r\n")
                out.writeBytes("Content-Type: $mime\r\n\r\n")
                resolver.openInputStream(uri)?.use { input -> input.copyTo(out) }
                out.writeBytes("\r\n--$boundary--\r\n")
                out.flush()
            }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val body = stream?.bufferedReader()?.use { it.readText() } ?: ""
            conn.disconnect()
            if (code !in 200..299) {
                val detail = runCatching { JSONObject(body).optString("detail", body) }.getOrDefault(body)
                error("HTTP $code: $detail")
            }
            val json = JSONObject(body)
            val id = json.optString("job_id", "")
            "JOB_ID=$id\nJob created • ${json.optString("status", "queued")}"
        }.getOrElse { "3D request failed: ${it.message}" }
        callback(result)
    }
}


fun check3dJob(urlText: String, jobId: String, token: String, callback: (String, String?) -> Unit) {
    thread {
        val result = runCatching {
            val base = urlText.trim().trimEnd('/')
            val conn = URL("$base/api/v1/3d/jobs/$jobId").openConnection() as HttpURLConnection
            conn.connectTimeout = 8000
            conn.readTimeout = 30000
            val code = conn.responseCode
            val body = (if (code in 200..299) conn.inputStream else conn.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            conn.disconnect()
            if (code !in 200..299) error("HTTP $code: $body")
            val json = JSONObject(body)
            val outputs = json.optJSONArray("outputs")
            val filename = if (outputs != null && outputs.length() > 0) {
                outputs.getJSONObject(0).optString("filename").takeIf { it.isNotBlank() }
            } else null
            val message = "Generation status: ${json.optString("status")}" +
                if (filename != null) " • Output ready: $filename" else
                    json.optString("message").takeIf { it.isNotBlank() }?.let { " • $it" }.orEmpty()
            message to filename
        }.getOrElse { "Status check failed: ${it.message}" to null }
        callback(result.first, result.second)
    }
}

fun download3dOutput(
    urlText: String,
    jobId: String,
    filename: String,
    destination: java.io.File,
    token: String,
    callback: (String) -> Unit
) {
    thread {
        val result = runCatching {
            val base = urlText.trim().trimEnd('/')
            val safeName = java.io.File(filename).name
            require(safeName.endsWith(".glb", ignoreCase = true))
            val conn = URL("$base/api/v1/3d/jobs/$jobId/outputs/$safeName").openConnection() as HttpURLConnection
            conn.connectTimeout = 10000
            conn.readTimeout = 180000
            if (token.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer $token")
            val code = conn.responseCode
            if (code !in 200..299) error("HTTP $code")
            val out = java.io.File(destination, safeName).canonicalFile
            require(out.parentFile == destination.canonicalFile)
            conn.inputStream.use { input -> out.outputStream().use(input::copyTo) }
            conn.disconnect()
            "Saved ${out.name} (${out.length()} bytes) in app workspace."
        }.getOrElse { "Download failed: ${it.message}" }
        callback(result)
    }
}
