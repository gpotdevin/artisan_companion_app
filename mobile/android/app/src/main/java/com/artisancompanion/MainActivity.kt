package com.artisancompanion

import android.annotation.SuppressLint
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * Thin Android shell: starts the embedded Python server (Chaquopy) on a
 * background thread, then loads the artisan-companion web UI in a WebView.
 *
 * The whole UI is the existing self-contained HTML served by FastAPI at
 * http://127.0.0.1:8000 — no UI rewrite.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private val handler = Handler(Looper.getMainLooper())
    private var loadAttempts = 0

    @SuppressLint("SetJavaScriptEnabled")
    @Suppress("DEPRECATION")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true

        // Retry the initial load until the Python server is up (startup race).
        webView.webViewClient = object : WebViewClient() {
            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                if (loadAttempts < 30) {
                    loadAttempts++
                    handler.postDelayed({ view?.loadUrl(URL) }, 500)
                }
            }
        }

        // Start embedded CPython.
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        // Default data lives in app-specific external storage (no permission
        // needed). Replace with a SAF-picked folder for real use (see
        // docs/mobile-port.md §3).
        val filesDir = getExternalFilesDir(null)?.absolutePath
            ?: filesDir.absolutePath
        val logsDir = "$filesDir/logs"
        val sensoryDir = "$filesDir/sensory"

        // Start the Python server on a background thread (it blocks).
        Thread {
            runCatching {
                val py = Python.getInstance()
                py.getModule("launcher").callAttr("start_server", logsDir, sensoryDir)
            }
        }.start()

        // First load attempt; WebViewClient retries on error.
        handler.postDelayed({ webView.loadUrl(URL) }, 1000)
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    companion object {
        private const val URL = "http://127.0.0.1:8000"
    }
}
