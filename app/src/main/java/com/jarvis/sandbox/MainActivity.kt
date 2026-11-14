package com.jarvis.sandbox

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Bg = Color(0xFF080D16)
private val Panel = Color(0xFF111B2B)
private val Accent = Color(0xFF55D6FF)
private val Muted = Color(0xFF91A4BC)

class MainActivity : ComponentActivity() {
    private lateinit var workspace: File

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        workspace = File(filesDir, "workspace").apply { mkdirs() }
        setContent { SandboxApp(workspace) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SandboxApp(workspace: File) {
    val context = LocalContext.current
    var page by remember { mutableStateOf("Home") }
    var refresh by remember { mutableIntStateOf(0) }
    var selectedFile by remember { mutableStateOf<File?>(null) }
    var output by remember { mutableStateOf("JARVIS SANDBOX runtime ready. Type 'help' to see supported commands.") }
    var command by remember { mutableStateOf("") }
    var agentTask by remember { mutableStateOf("") }
    var taskLog by remember { mutableStateOf("Agent is idle. No external AI connection configured.") }
    var showConfirm by remember { mutableStateOf<File?>(null) }
    var workerUrl by remember { mutableStateOf("http://127.0.0.1:8765") }
    var workerToken by remember { mutableStateOf("") }
    var workerStatus by remember { mutableStateOf("Not checked") }
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    var imageName by remember { mutableStateOf<String?>(null) }
    var threeDStatus by remember { mutableStateOf("Choose an image to begin.") }
    var threeDJobId by remember { mutableStateOf<String?>(null) }
    var threeDOutput by remember { mutableStateOf<String?>(null) }

    val imageLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) {
            imageUri = uri
            imageName = queryName(context.contentResolver, uri) ?: "reference image"
            threeDStatus = "Image selected. Test the worker, then request generation."
        }
    }

    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) {
            runCatching {
                val name = queryName(context.contentResolver, uri) ?: "import_${System.currentTimeMillis()}"
                val safe = File(workspace, name).canonicalFile
                require(safe.parentFile == workspace.canonicalFile)
                context.contentResolver.openInputStream(uri)?.use { input -> safe.outputStream().use(input::copyTo) }
                refresh++
                output = "Imported: ${safe.name}"
            }.onFailure { output = "Import failed: ${it.message}" }
        }
    }
    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri: Uri? ->
        val file = selectedFile
        if (uri != null && file != null && file.isFile) {
            runCatching {
                context.contentResolver.openOutputStream(uri)?.use { out -> file.inputStream().use { input -> input.copyTo(out) } }
                output = "Exported: ${file.name}"
            }.onFailure { output = "Export failed: ${it.message}" }
        }
    }

    MaterialTheme(colorScheme = darkColorScheme(
        background = Bg, surface = Panel, primary = Accent,
        onBackground = Color.White, onSurface = Color.White
    )) {
        Scaffold(
            containerColor = Bg,
            topBar = {
                TopAppBar(
                    title = {
                        Column {
                            Text("JARVIS SANDBOX", fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                            Text("LOCAL WORKSPACE  •  v0.2.0", color = Muted, fontSize = 10.sp, letterSpacing = 1.sp)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Bg),
                    actions = { Icon(Icons.Default.Shield, null, tint = Accent, modifier = Modifier.padding(end = 16.dp)) }
                )
            },
            bottomBar = {
                NavigationBar(containerColor = Panel) {
                    listOf("Home", "Files", "Terminal", "Agent", "Bridge", "3D Lab").forEach { item ->
                        NavigationBarItem(
                            selected = page == item,
                            onClick = { page = item },
                            icon = {
                                Icon(when(item) {
                                    "Home" -> Icons.Default.Dashboard
                                    "Files" -> Icons.Default.Folder
                                    "Terminal" -> Icons.Default.Terminal
                                    "Agent" -> Icons.Default.Psychology
                                    "Bridge" -> Icons.Default.ViewInAr
                                    else -> Icons.Default.Polymer
                                }, contentDescription = item)
                            },
                            label = { Text(item) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Accent, selectedTextColor = Accent,
                                indicatorColor = Color(0xFF20364B), unselectedTextColor = Muted
                            )
                        )
                    }
                }
            }
        ) { padding ->
            Box(Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
                when(page) {
                    "Home" -> HomeScreen(workspace, onNavigate = { page = it })
                    "Files" -> FilesScreen(workspace, refresh, onImport = {
                        importLauncher.launch(arrayOf("*/*"))
                    }, onSelect = { selectedFile = it; page = "File detail" })
                    "File detail" -> FileDetailScreen(selectedFile, onBack = { page = "Files" }, onExport = {
                        selectedFile?.let { exportLauncher.launch(it.name) }
                    }, onDelete = { file ->
                        showConfirm = file
                    })
                    "Terminal" -> TerminalScreen(command, { command = it }, output, {
                        output = runSafeCommand(workspace, command)
                        command = ""
                        refresh++
                    })
                    "Agent" -> AgentScreen(agentTask, { agentTask = it }, taskLog, {
                        taskLog = if (agentTask.isBlank()) "Enter a task first." else
                            "TASK QUEUED (local draft)\n$agentTask\n\nNo AI provider is connected yet. The agent API and approval gateway are integration milestones."
                    })
                    "Bridge" -> BridgeScreen(onImport = { importLauncher.launch(arrayOf("*/*")) })
                    "3D Lab" -> ThreeDLabScreen(
                        workerUrl = workerUrl,
                        onWorkerUrlChange = { workerUrl = it },
                        workerToken = workerToken,
                        onWorkerTokenChange = { workerToken = it },
                        imageName = imageName,
                        connectionStatus = workerStatus,
                        jobStatus = threeDStatus,
                        hasJob = threeDJobId != null,
                        hasOutput = threeDOutput != null,
                        onChooseImage = { imageLauncher.launch(arrayOf("image/*")) },
                        onCheckWorker = { checkWorker(workerUrl) { result -> workerStatus = result } },
                        onGenerate = {
                            val uri = imageUri
                            if (uri != null) submitImageTo3d(context.contentResolver, uri, workerUrl, workerToken) { result ->
                                threeDStatus = result
                                threeDJobId = Regex("JOB_ID=([a-f0-9-]+)").find(result)?.groupValues?.getOrNull(1)
                                threeDOutput = null
                            }
                        },
                        onCheckJob = {
                            val id = threeDJobId
                            if (id != null) check3dJob(workerUrl, id, workerToken) { result, filename ->
                                threeDStatus = result
                                if (filename != null) threeDOutput = filename
                            }
                        },
                        onDownloadOutput = {
                            val id = threeDJobId
                            val filename = threeDOutput
                            if (id != null && filename != null) download3dOutput(workerUrl, id, filename, workspace, workerToken) { result ->
                                threeDStatus = result
                                refresh++
                            }
                        }
                    )
                }
            }
        }
    }
    if (showConfirm != null) {
        AlertDialog(
            onDismissRequest = { showConfirm = null },
            title = { Text("Delete file?") },
            text = { Text("This permanently deletes ${showConfirm?.name} from the app workspace.") },
            confirmButton = {
                TextButton(onClick = {
                    showConfirm?.delete()
                    showConfirm = null
                    selectedFile = null
                    refresh++
                    page = "Files"
                }) { Text("Delete", color = Color.Red) }
            },
            dismissButton = { TextButton(onClick = { showConfirm = null }) { Text("Cancel") } }
        )
    }
}

@Composable
fun HomeScreen(workspace: File, onNavigate: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Your workspace. Your tools. Your JARVIS.", fontSize = 23.sp, fontWeight = FontWeight.Bold)
        Text("A local-first control center for building JARVIS and creating digital assets.", color = Muted)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard("WORKSPACE", "${workspace.walkTopDown().count { it.isFile }} files", Modifier.weight(1f))
            StatCard("EXECUTION", "Restricted", Modifier.weight(1f))
        }
        Text("WORKBENCH", color = Accent, fontWeight = FontWeight.Bold, letterSpacing = 1.4.sp)
        listOf(
            Triple("Files", "Manage project files in the private workspace", Icons.Default.Folder),
            Triple("Terminal", "Run safe built-in workspace commands", Icons.Default.Terminal),
            Triple("Agent", "Queue tasks and connect an AI operator later", Icons.Default.Psychology),
            Triple("Bridge", "Import Blender models and exchange project assets", Icons.Default.ViewInAr)
        ).forEach { (name, desc, icon) ->
            Card(colors = CardDefaults.cardColors(containerColor = Panel), modifier = Modifier.fillMaxWidth().clickable { onNavigate(name) }) {
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(icon, null, tint = Accent, modifier = Modifier.size(30.dp))
                    Spacer(Modifier.width(14.dp))
                    Column(Modifier.weight(1f)) { Text(name, fontWeight = FontWeight.Bold); Text(desc, color = Muted, fontSize = 12.sp) }
                    Icon(Icons.Default.ChevronRight, null, tint = Muted)
                }
            }
        }
        Text("Safety: file access is limited to this app workspace unless you explicitly import or export files.", color = Muted, fontSize = 11.sp)
    }
}

@Composable
fun StatCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier, colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(Modifier.padding(14.dp)) {
            Text(title, color = Muted, fontSize = 10.sp, letterSpacing = 1.sp)
            Text(value, fontWeight = FontWeight.Bold, color = Accent)
        }
    }
}

@Composable
fun FilesScreen(workspace: File, refresh: Int, onImport: () -> Unit, onSelect: (File) -> Unit) {
    val files = remember(refresh) { workspace.listFiles()?.sortedBy { it.name.lowercase() } ?: emptyList() }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Workspace files", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text("/workspace", color = Muted, fontSize = 12.sp)
            }
            Button(onClick = onImport) { Icon(Icons.Default.FileDownload, null); Text(" Import") }
        }
        if (files.isEmpty()) Text("No files yet. Import a model, image, source file or project archive.", color = Muted)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(files) { file ->
                Card(colors = CardDefaults.cardColors(containerColor = Panel), modifier = Modifier.fillMaxWidth().clickable { onSelect(file) }) {
                    Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(if (file.isDirectory) Icons.Default.Folder else Icons.Default.InsertDriveFile, null, tint = Accent)
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(file.name, fontWeight = FontWeight.Medium)
                            Text(if (file.isDirectory) "Folder" else "${file.length()} bytes", color = Muted, fontSize = 11.sp)
                        }
                        Icon(Icons.Default.ChevronRight, null, tint = Muted)
                    }
                }
            }
        }
    }
}

@Composable
fun FileDetailScreen(file: File?, onBack: () -> Unit, onExport: () -> Unit, onDelete: (File) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = onBack) { Text("← Back to files") }
        Text(file?.name ?: "No file selected", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text(file?.let { if (it.isDirectory) "Directory" else "${it.length()} bytes • ${it.extension}" } ?: "", color = Muted)
        if (file?.isFile == true) Button(onClick = onExport, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.FileUpload, null); Text(" Export file") }
        if (file != null) OutlinedButton(onClick = { onDelete(file) }, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.Delete, null); Text(" Delete") }
        Text("Files are stored in the app-private workspace. Export creates a copy; it does not move the original.", color = Muted, fontSize = 12.sp)
    }
}

@Composable
fun TerminalScreen(command: String, onCommand: (String) -> Unit, output: String, onRun: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Workspace terminal", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("Restricted command interpreter • no arbitrary shell execution", color = Muted, fontSize = 12.sp)
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF05080D)), modifier = Modifier.weight(1f).fillMaxWidth()) {
            Text(output, Modifier.padding(14.dp), color = Color(0xFFB7F6D2), fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(command, onCommand, modifier = Modifier.weight(1f), label = { Text("Command") }, singleLine = true)
            Spacer(Modifier.width(8.dp))
            Button(onClick = onRun) { Icon(Icons.Default.PlayArrow, null) }
        }
        Text("Try: help, pwd, ls, mkdir models, touch notes.txt, write notes.txt hello, cat notes.txt", color = Muted, fontSize = 11.sp)
    }
}

@Composable
fun AgentScreen(task: String, onTask: (String) -> Unit, log: String, onQueue: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("AI Operator", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.RadioButtonChecked, null, tint = Color(0xFFFFC66D))
            Spacer(Modifier.width(8.dp))
            Text("Not connected • local task queue only", color = Muted, fontSize = 12.sp)
        }
        OutlinedTextField(task, onTask, modifier = Modifier.fillMaxWidth().weight(0.35f), label = { Text("Describe a task for JARVIS") }, minLines = 4)
        Button(onClick = onQueue, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.AddTask, null); Text(" Queue task") }
        Card(colors = CardDefaults.cardColors(containerColor = Panel), modifier = Modifier.fillMaxWidth()) {
            Text(log, Modifier.padding(14.dp), fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        }
        Text("Planned integration: local GGUF inference, optional remote model, tool registry, approval prompts, audit log and rollback snapshots.", color = Muted, fontSize = 12.sp)
    }
}

@Composable
fun BridgeScreen(onImport: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("3D & Blender bridge", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("Exchange assets with Blender for Android using Android's document picker.", color = Muted)
        Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Default.ViewInAr, tint = Accent, contentDescription = null, modifier = Modifier.size(36.dp))
                Text("Import Blender assets", fontWeight = FontWeight.Bold)
                Text("Bring .blend, .fbx, .obj, .glb, .gltf, textures and ZIP files into the JARVIS workspace.", color = Muted, fontSize = 12.sp)
                Button(onClick = onImport) { Text("Choose files") }
            }
        }
        Text("Current bridge: file exchange. Direct Blender automation, viewport control and model conversion require a separate Blender-side integration or a compatible local/PC worker; this starter does not pretend those APIs exist.", color = Muted, fontSize = 12.sp)
    }
}

private fun runSafeCommand(root: File, raw: String): String {
    val parts = raw.trim().split(Regex("\\s+"), limit = 3)
    if (parts.isEmpty() || parts[0].isBlank()) return "Enter a command."
    fun target(name: String): File {
        require(name.isNotBlank() && !name.contains("/") && !name.contains("\\"))
        val f = File(root, name).canonicalFile
        require(f.parentFile == root.canonicalFile) { "Only workspace root files are supported in v0.1." }
        return f
    }
    return try {
        when(parts[0]) {
            "help" -> "Commands:\nhelp\npwd\nls\nmkdir NAME\ntouch NAME\nwrite NAME TEXT\ncat NAME\nrm NAME\n\nOnly files in workspace root are supported."
            "pwd" -> "/workspace"
            "ls" -> root.list()?.sorted()?.joinToString("\n") ?: "(empty)"
            "mkdir" -> { require(parts.size >= 2); target(parts[1]).mkdir(); "Folder created: ${parts[1]}" }
            "touch" -> { require(parts.size >= 2); target(parts[1]).apply { if (!exists()) createNewFile() }; "File ready: ${parts[1]}" }
            "write" -> {
                require(parts.size == 3)
                val f = target(parts[1])
                f.writeText(parts[2])
                "Wrote ${f.length()} bytes to ${f.name}"
            }
            "cat" -> { require(parts.size >= 2); val f = target(parts[1]); require(f.isFile); f.readText().take(12000) }
            "rm" -> { require(parts.size >= 2); val f = target(parts[1]); require(f.exists() && f.isFile); f.delete(); "Deleted ${parts[1]}" }
            else -> "Command not allowed: ${parts[0]}. Type help."
        }
    } catch(e: Exception) { "Error: ${e.message ?: "operation failed"}" }
}

private fun queryName(resolver: android.content.ContentResolver, uri: Uri): String? {
    resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
        if (it.moveToFirst()) return it.getString(0)
    }
    return null
}
