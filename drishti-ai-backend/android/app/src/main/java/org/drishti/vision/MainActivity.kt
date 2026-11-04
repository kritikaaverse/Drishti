package org.drishti.vision

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Bundle
import android.os.Build
import android.os.Vibrator
import android.os.VibratorManager
import android.os.VibrationEffect
import android.content.Context
import android.speech.tts.UtteranceProgressListener
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import android.text.InputType
import android.view.View
import android.view.WindowManager
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import android.util.Size
import okhttp3.*
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.Locale
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Native Android rear camera -> binary JPEG WebSocket -> laptop -> Android TTS.
 * The source is not a medical/safety product. No audio/images go to external AI APIs.
 */
class MainActivity : ComponentActivity(), TextToSpeech.OnInitListener {
    private lateinit var server: EditText
    private lateinit var key: EditText
    private lateinit var languages: Spinner
    private lateinit var status: TextView
    private lateinit var resultText: TextView
    private lateinit var preview: PreviewView
    private lateinit var tts: TextToSpeech
    private var ttsReady = false
    @Volatile private var vibrationEnabled = true
    @Volatile private var voiceEnabled = true
    private var lastVibration = 0L
    private var speechActive = false
    private data class Spoken(val text: String, val locale: String, val priority: String, val at: Long)
    private val speechQueue = java.util.ArrayDeque<Spoken>()
    private val handler = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private val client = OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS).build()
    private var cameraProvider: ProcessCameraProvider? = null
    @Volatile private var socket: WebSocket? = null
    @Volatile private var running = false
    private val ready = AtomicBoolean(false)
    private val waiting = AtomicBoolean(false)
    private var lastSent = 0L
    private var ackDeadline = 0L
    private var retryDelay = 1000L
    @Volatile private var generation = 0
    private var lastDisconnectSpoken = 0L
    private val locales = listOf("en-IN", "hi-IN", "mr-IN")
    private val codes = listOf("en", "hi", "mr")
    private val prefs by lazy { getSharedPreferences("drishti", MODE_PRIVATE) }
    private val deviceId by lazy { prefs.getString("device_id", null) ?: ("android-" + UUID.randomUUID()).also { prefs.edit().putString("device_id", it).apply() } }
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startSession() else show("Camera permission is required. No frames were sent.")
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 20, 24, 20) }
        val scroll = ScrollView(this).apply { addView(column) }
        column.addView(TextView(this).apply { text = "Drishti · Phone Camera"; textSize = 25f; setTextColor(0xff182746.toInt()) })
        column.addView(TextView(this).apply { text = "Assistive prototype. Keep using your cane, guide dog or human support. No camera can guarantee a safe path."; textSize = 15f; setPadding(0, 15, 0, 15) })
        server = EditText(this).apply { hint = "Laptop URL, e.g. http://192.168.1.10:8000"; inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI; setText(prefs.getString("server", "")); contentDescription = "Laptop backend URL"; minHeight = 100 }
        key = EditText(this).apply { hint = "Backend API key"; inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD; contentDescription = "Backend API key"; minHeight = 100 }
        languages = Spinner(this).apply { adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, listOf("English", "हिन्दी", "मराठी")); contentDescription = "Voice language"; minimumHeight = 100; setSelection(prefs.getInt("language", 0).coerceIn(0,2)) }
        column.addView(server); column.addView(key); column.addView(languages)
        column.addView(Switch(this).apply {
            text = "Speak detected objects"; isChecked = prefs.getBoolean("voice_enabled",true); voiceEnabled=isChecked; minHeight=100
            setOnCheckedChangeListener { _, enabled -> voiceEnabled=enabled; prefs.edit().putBoolean("voice_enabled",enabled).apply(); if(!enabled) { speechQueue.clear(); speechActive=false; tts.stop() } }
        })
        column.addView(Switch(this).apply {
            text = "Vibrate for new detections"; isChecked = prefs.getBoolean("vibration_enabled",true); vibrationEnabled=isChecked; minHeight=100
            setOnCheckedChangeListener { _, enabled -> vibrationEnabled=enabled; prefs.edit().putBoolean("vibration_enabled",enabled).apply(); if(enabled) vibrateDetection(longArrayOf(0,120)) }
        })
        column.addView(Button(this).apply { text = "Start Android rear camera"; minHeight = 100; setOnClickListener { if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) startSession() else permission.launch(Manifest.permission.CAMERA) } })
        column.addView(Button(this).apply { text = "Stop camera and speech"; minHeight = 100; setOnClickListener { stopSession(); show("Camera stopped.") } })
        status = TextView(this).apply { text = "Disconnected"; textSize = 17f; accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE; setPadding(0,15,0,15) }
        column.addView(status)
        preview = PreviewView(this).apply { contentDescription = "Android rear camera preview" }
        column.addView(preview, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 500))
        resultText = TextView(this).apply { textSize = 16f; setPadding(0,15,0,15) }
        column.addView(resultText)
        setContentView(scroll)
        tts = TextToSpeech(this, this)
        languages.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                prefs.edit().putInt("language", position).apply()
                if (ttsReady) tts.language = Locale.forLanguageTag(locales[position])
                if (running) { stopSession(); show("Language changed. Tap Start to reconnect.") }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }
    override fun onInit(code: Int) {
        ttsReady = code == TextToSpeech.SUCCESS
        if (ttsReady) {
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) { handler.post { speechActive=false; playNextSpeech() } }
                @Deprecated("Android legacy callback")
                override fun onError(utteranceId: String?) { handler.post { speechActive=false; playNextSpeech() } }
            })
            val available = tts.setLanguage(Locale.forLanguageTag(locales[languages.selectedItemPosition]))
            if (available < TextToSpeech.LANG_AVAILABLE) show("Install the selected offline voice in Android Text-to-Speech settings.")
        } else show("Text-to-Speech is unavailable on this phone.")
    }
    private fun show(text: String) { runOnUiThread { status.text = text } }
    private fun say(message: String, locale: String, priority: String = "high") {
        runOnUiThread {
            if (!ttsReady || !voiceEnabled || message.isBlank()) return@runOnUiThread
            if (speechQueue.size >= 2) speechQueue.removeFirst() // Never grow a stale narration backlog.
            speechQueue.addLast(Spoken(message,locale,priority,SystemClock.elapsedRealtime()))
            if (!speechActive) playNextSpeech()
        }
    }
    private fun playNextSpeech() {
        if (!ttsReady || !voiceEnabled || speechActive) return
        while (speechQueue.isNotEmpty()) {
            val item=speechQueue.removeFirst()
            if(SystemClock.elapsedRealtime()-item.at>12000) continue // Do not narrate stale camera observations.
            if(tts.setLanguage(Locale.forLanguageTag(item.locale))<TextToSpeech.LANG_AVAILABLE) {
                show("Missing voice pack for ${item.locale}. Install it in Android settings."); continue
            }
            speechActive=true
            if(tts.speak(item.text,TextToSpeech.QUEUE_FLUSH,null,UUID.randomUUID().toString())==TextToSpeech.ERROR) speechActive=false
            return
        }
    }
    private fun vibrateDetection(pattern: LongArray) {
        if(!vibrationEnabled) return
        val now=SystemClock.elapsedRealtime()
        if(now-lastVibration<1500) return
        lastVibration=now
        runOnUiThread {
            val vibrator=if(Build.VERSION.SDK_INT>=31) getSystemService(VibratorManager::class.java).defaultVibrator
                else @Suppress("DEPRECATION") (getSystemService(Context.VIBRATOR_SERVICE) as Vibrator)
            if(vibrator.hasVibrator()) vibrator.vibrate(VibrationEffect.createWaveform(pattern,-1))
            else show("This device has no vibration motor. Voice and screen feedback remain available.")
        }
    }
    private fun startSession() {
        stopSession()
        val url = server.text.toString().trim().removeSuffix("/")
        val parsed = try { java.net.URI(url) } catch (_: Exception) { null }
        if (parsed?.host == null || parsed.scheme !in listOf("http", "https")) { show("Enter your laptop LAN URL, not the phone's localhost."); return }
        if (!BuildConfig.DEBUG && parsed.scheme != "https") { show("Release builds require HTTPS with a trusted certificate."); return }
        if (parsed.host in listOf("localhost", "127.0.0.1") && !BuildConfig.DEBUG) { show("Use your laptop hostname or LAN address."); return }
        prefs.edit().putString("server", url).apply()
        running = true
        val current = ++generation
        retryDelay = 1000
        connect(url, current)
        val provider = ProcessCameraProvider.getInstance(this)
        provider.addListener({
            if (!running) return@addListener
            try {
                cameraProvider = provider.get()
                val cameraPreview = Preview.Builder().build().also { it.surfaceProvider = preview.surfaceProvider }
                val resolution = ResolutionSelector.Builder().setResolutionStrategy(ResolutionStrategy(Size(640,480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER)).build()
                val analysis = ImageAnalysis.Builder().setResolutionSelector(resolution).setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888).setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                analysis.setAnalyzer(worker) { image -> analyze(image) }
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, cameraPreview, analysis)
            } catch (e: Exception) { stopSession(); show("Rear camera unavailable: ${e.message}") }
        }, ContextCompat.getMainExecutor(this))
    }
    private fun connect(url: String, current: Int) {
        if (!running || current != generation) return
        ready.set(false)
        waiting.set(false)
        val wsUrl = url.replaceFirst("https://", "wss://").replaceFirst("http://", "ws://") + "/api/ws/vision"
        val language = codes[languages.selectedItemPosition]
        val secret = key.text.toString() // Kept in memory only, never saved or logged.
        show("Connecting to laptop…")
        socket = client.newWebSocket(Request.Builder().url(wsUrl).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                if (!running || current != generation) { webSocket.close(1000,"Stopped"); return }
                webSocket.send(JSONObject().put("role","camera").put("device_id",deviceId).put("language",language).put("api_key",secret).put("mode","obstacle").toString())
            }
            override fun onMessage(webSocket: WebSocket, text: String) {
                if (!running || current != generation) return
                try {
                    val data = JSONObject(text)
                    when(data.optString("type")) {
                        "ready" -> { ready.set(true); retryDelay = 1000; show("Connected · rear camera · max 1 processed frame/sec") }
                        "detections" -> {
                            waiting.set(false)
                            val voice = data.optJSONObject("voice")
                            if (voice != null && !voice.optBoolean("suppressed")) say(voice.optString("message"), voice.optString("tts_locale","en-IN"), voice.optString("priority","low"))
                            val haptic=data.optJSONObject("haptic")
                            if(haptic?.optBoolean("vibrate")==true) {
                                val values=haptic.optJSONArray("pattern_ms")
                                val pattern=if(values!=null && values.length() in 1..8) LongArray(values.length()) { values.optLong(it,0).coerceIn(0,500) } else longArrayOf(0,120)
                                vibrateDetection(pattern)
                            }
                            val objects = data.optJSONArray("detections")
                            val summary = buildString {
                                append("${data.optDouble("inference_ms").toInt()} ms · Distance unavailable\n")
                                if (objects != null) for (i in 0 until objects.length()) {
                                    val d=objects.getJSONObject(i)
                                    append("${d.optString("name")} · ${d.optString("position")} · ${(d.optDouble("confidence")*100).toInt()}%\n")
                                }
                            }
                            runOnUiThread { resultText.text = summary }
                        }
                    }
                    if (!data.optBoolean("success",true)) { waiting.set(false); show(data.optString("error","Processing error")) }
                } catch (_: Exception) { waiting.set(false); show("Could not read server response.") }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) { reconnect(url,current) }
            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(code, reason)
                if (code == 1008) { running=false; ready.set(false); runOnUiThread { cameraProvider?.unbindAll() }; show("Connection rejected. Check API key or duplicate device session.") }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) { if (code != 1008) reconnect(url,current) }
        })
    }
    @Synchronized private fun reconnect(url: String, current: Int) {
        if (!running || current != generation) return
        ready.set(false); waiting.set(false)
        val next = ++generation
        show("Laptop disconnected. Reconnecting…")
        if (SystemClock.elapsedRealtime()-lastDisconnectSpoken > 15000) {
            lastDisconnectSpoken=SystemClock.elapsedRealtime()
            val index=prefs.getInt("language",0).coerceIn(0,2)
            say(listOf("Phone connection lost. Visual assistance unavailable.","फोन कनेक्शन टूट गया। दृश्य सहायता उपलब्ध नहीं है।","फोनचा संपर्क तुटला. दृश्य सहाय्य उपलब्ध नाही.")[index],locales[index])
        }
        val delay=retryDelay
        retryDelay=(retryDelay*2).coerceAtMost(15000)
        handler.postDelayed({ connect(url,next) },delay)
    }
    private fun analyze(image: ImageProxy) {
        try {
            val now=SystemClock.elapsedRealtime()
            if (waiting.get() && now>ackDeadline) { socket?.cancel(); waiting.set(false) }
            if (!running || !ready.get() || waiting.get() || now-lastSent<1000) return
            val plane=image.planes[0]
            val packed=ByteBuffer.allocate(image.width*image.height*4)
            val row=ByteArray(image.width*4)
            val source=plane.buffer.duplicate()
            for (y in 0 until image.height) {
                source.position(y*plane.rowStride)
                source.get(row)
                packed.put(row)
            }
            packed.rewind()
            val padded=Bitmap.createBitmap(image.width,image.height,Bitmap.Config.ARGB_8888)
            padded.copyPixelsFromBuffer(packed)
            val cropped=padded
            val rotation=Matrix().apply { postRotate(image.imageInfo.rotationDegrees.toFloat()) }
            val oriented=Bitmap.createBitmap(cropped,0,0,cropped.width,cropped.height,rotation,true)
            val scale=640f/maxOf(oriented.width,oriented.height)
            val resized=if(scale<1) Bitmap.createScaledBitmap(oriented,(oriented.width*scale).toInt(),(oriented.height*scale).toInt(),true) else oriented
            val output=ByteArrayOutputStream()
            resized.compress(Bitmap.CompressFormat.JPEG,70,output)
            val payload=output.toByteArray()
            if(payload.size>4*1024*1024) { show("Compressed frame exceeds backend limit."); return }
            waiting.set(true)
            ackDeadline=now+45000
            lastSent=now
            if(socket?.send(payload.toByteString())!=true) waiting.set(false)
            // Identity-based recycling avoids double recycling when createBitmap reuses a bitmap.
            val bitmaps=listOf(resized,oriented,cropped,padded)
            bitmaps.forEachIndexed { index, bitmap -> if (bitmaps.take(index).none { it === bitmap } && !bitmap.isRecycled) bitmap.recycle() }
        } catch (_: Exception) { waiting.set(false); show("Frame conversion failed; trying next frame.") }
        finally { image.close() }
    }
    private fun stopSession() {
        running=false; generation++; ready.set(false); waiting.set(false)
        handler.removeCallbacksAndMessages(null)
        socket?.close(1000,"User stopped"); socket=null
        cameraProvider?.unbindAll()
        speechQueue.clear(); speechActive=false
        if (::tts.isInitialized) tts.stop()
    }
    override fun onStop() { super.onStop(); stopSession(); show("Camera paused. Tap Start to resume.") }
    override fun onDestroy() { stopSession(); worker.shutdown(); client.dispatcher.executorService.shutdown(); client.connectionPool.evictAll(); if (::tts.isInitialized) tts.shutdown(); super.onDestroy() }
}
