
package com.jarvis.sandbox

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Build
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class ExternalNanobotService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        ExternalNanobotBridge.attach(this)
        publishSnapshot()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        publishSnapshot()
    }

    override fun onInterrupt() {
        ExternalNanobotBridge.status = "Interrupted by Android"
    }

    override fun onDestroy() {
        ExternalNanobotBridge.detach(this)
        super.onDestroy()
    }

    private fun publishSnapshot() {
        val root = rootInActiveWindow ?: return
        val nodes = mutableListOf<ExternalUiNode>()
        collectNodes(root, nodes, 0)

        ExternalNanobotBridge.latestSnapshot = ExternalUiSnapshot(
            root.packageName?.toString() ?: "unknown",
            root.contentDescription?.toString().orEmpty(),
            nodes,
            System.currentTimeMillis()
        )
        root.recycle()
    }

    private fun collectNodes(
        node: AccessibilityNodeInfo,
        out: MutableList<ExternalUiNode>,
        depth: Int
    ) {
        if (out.size >= 80 || depth > 12) return

        val bounds = android.graphics.Rect()
        node.getBoundsInScreen(bounds)

        out += ExternalUiNode(
            node.text?.toString().orEmpty(),
            node.contentDescription?.toString().orEmpty(),
            node.className?.toString().orEmpty(),
            node.viewIdResourceName.orEmpty(),
            node.isClickable,
            node.isEditable,
            node.isScrollable,
            node.isEnabled,
            bounds.left, bounds.top, bounds.right, bounds.bottom,
            depth
        )

        for (i in 0 until node.childCount) {
            if (out.size >= 80) break
            val child = node.getChild(i) ?: continue
            collectNodes(child, out, depth + 1)
            child.recycle()
        }
    }

    private fun findNode(
        root: AccessibilityNodeInfo,
        test: (AccessibilityNodeInfo) -> Boolean
    ): AccessibilityNodeInfo? {
        if (test(root)) return AccessibilityNodeInfo.obtain(root)

        for (i in 0 until root.childCount) {
            val child = root.getChild(i) ?: continue
            val found = findNode(child, test)
            child.recycle()
            if (found != null) return found
        }
        return null
    }

    fun clickText(target: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNode(root) {
            it.isClickable &&
            (it.text?.toString()?.equals(target, true) == true ||
             it.contentDescription?.toString()?.equals(target, true) == true)
        }
        val result =
            node?.performAction(AccessibilityNodeInfo.ACTION_CLICK) == true
        node?.recycle()
        root.recycle()
        return result
    }

    fun setFocusedText(value: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNode(root) { it.isFocused && it.isEditable }

        val args = android.os.Bundle().apply {
            putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                value
            )
        }

        val result =
            node?.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args) == true

        node?.recycle()
        root.recycle()
        return result
    }

    fun scroll(forward: Boolean): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNode(root) { it.isScrollable }

        val action = if (forward)
            AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
        else
            AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD

        val result = node?.performAction(action) == true
        node?.recycle()
        root.recycle()
        return result
    }

    fun tap(x: Float, y: Float): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return false

        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(
                GestureDescription.StrokeDescription(path, 0, 80)
            )
            .build()

        return dispatchGesture(gesture, null, null)
    }

    fun back() = performGlobalAction(GLOBAL_ACTION_BACK)
    fun home() = performGlobalAction(GLOBAL_ACTION_HOME)
}

data class ExternalUiNode(
    val text: String,
    val description: String,
    val className: String,
    val viewId: String,
    val clickable: Boolean,
    val editable: Boolean,
    val scrollable: Boolean,
    val enabled: Boolean,
    val left: Int,
    val top: Int,
    val right: Int,
    val bottom: Int,
    val depth: Int
)

data class ExternalUiSnapshot(
    val packageName: String,
    val windowTitle: String,
    val nodes: List<ExternalUiNode>,
    val capturedAt: Long
)

object ExternalNanobotBridge {
    @Volatile private var service: ExternalNanobotService? = null

    @Volatile
    var latestSnapshot: ExternalUiSnapshot? = null

    @Volatile
    var status: String = "Accessibility service not enabled"

    internal fun attach(value: ExternalNanobotService) {
        service = value
        status = "Connected"
    }

    internal fun detach(value: ExternalNanobotService) {
        if (service === value) {
            service = null
            status = "Disconnected"
        }
    }

    fun isConnected() = service != null

    fun clickText(value: String) =
        service?.clickText(value) ?: false

    fun setFocusedText(value: String) =
        service?.setFocusedText(value) ?: false

    fun scrollForward() =
        service?.scroll(true) ?: false

    fun scrollBackward() =
        service?.scroll(false) ?: false

    fun tap(x: Float, y: Float) =
        service?.tap(x, y) ?: false

    fun back() = service?.back() ?: false
    fun home() = service?.home() ?: false
}
