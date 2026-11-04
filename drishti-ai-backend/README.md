# Drishti — Android Camera Blind-Assistance Backend

**Functional local assistive MVP, production-structured — not a certified mobility or medical device.** Python 3.11, FastAPI, local YOLOv8n, OpenCV, local Tesseract, SQLite, WebSocket, Android native TTS. The existing React Drishti UI is integrated in the sibling `drishti-ai` folder.

```
Android rear camera → Wi-Fi JPEG → laptop FastAPI → YOLO/OpenCV/OCR
                                              ↓
Android TextToSpeech ← JSON results/voice ← WebSocket
React laptop dashboard ← observer WebSocket + authenticated frame snapshots
```

**No laptop webcam is opened. No ESP32 is required. No external vision/LLM service receives frames.**

## What works, and what does not

Implemented and exercised with real inference:
- Actual YOLOv8n detection; model loaded once per server; CPU default, optional configured CUDA/MPS device.
- Confidence, original-image pixel boxes, left/center/right, class ID, heuristic relevance priority, best-effort per-device tracking IDs for phone frames.
- Actual English, Hindi and Marathi Tesseract OCR with real engine confidence when available.
- Evidence-bound object-count scene summaries, not invented room/traffic descriptions.
- Short English/Hindi/Marathi warning templates, configurable cooldown, duplicate suppression, priority override and client-native TTS payloads.
- REST phone frames, binary WebSocket phone frames, observer WebSocket broadcasts, bounded latest-only observer queues, JPEG byte/dimension validation, frame throttling and CPU busy backpressure.
- Camera heartbeat, expiry, authenticated JPEG snapshots/MJPEG, SQLite inference history, pagination/deletion, API-key auth and explicit CORS.
- React real results, OCR, summaries, history, device capabilities and live phone preview.

Explicit limitations:
- **No validated depth model. Every distance is `null` and `distance_type` is `not_available`.** Box size affects relevance only, not meters or collision imminence.
- **No GPS routing or safe-path planner.** `/navigation/guidance` is camera observation only and returns `routing_available=false`. The React route map is separately labeled illustrative.
- **No detailed vision-language model.** Indoor/outdoor/room type cannot reliably be inferred from a short object list. `scene_method=detected_objects_summary`. Integrating and validating a real VLM is future work, not a hidden stub or fake output.
- Default COCO YOLO recognizes 80 classes, including person, vehicles, animals, furniture, bottles, bags and electronics. It does **not** distinguish children from adults, detect all signs, decode traffic-light colors, or cover generic doors, windows, walls, poles, stairs, curbs, potholes and zebra crossings. Use and validate a custom-trained compatible model for those classes; `/device/status` reports actual class names.
- Tracker is an implemented class-aware greedy IoU association tracker, **not ByteTrack**. It works best at higher FPS and may change IDs at 1–2 FPS; IDs are not human identities.
- Native Android source is supplied, but **not compiled or tested on a physical phone in this environment**. Build, camera permissions, orientation, Wi-Fi reconnects, TTS packs and TalkBack must be validated on target devices. There is no supplied APK.
- Battery/Wi-Fi/sensors return `null` unless independently implemented; no fake device telemetry.
- No recognition benchmark, safety certification or WCAG/Android accessibility certification is claimed.

## Folder structure

```
drishti-ai-backend/
  main.py                        # lifespan, routes, auth/error/logging/docs
  config.py                      # Pydantic environment settings
  requirements.txt
  .env.example
  api/
    common.py camera.py detection.py ocr.py scene.py navigation.py voice.py device.py
  ai/
    yolo_detector.py object_tracker.py obstacle_detection.py depth_estimation.py
    scene_understanding.py ocr_engine.py
  services/
    frame_processor.py priority_manager.py voice_service.py history_service.py
    body_limit.py errors.py
  database/
    db.py models.py
  scripts/
    download_models.py run_server.py camera_upload_client.py
  static/camera-sender.html       # Android browser fallback (HTTPS required)
  android/                       # native CameraX + WebSocket + TextToSpeech project
  tests/
    conftest.py test_detection.py test_ocr.py test_api.py fixtures/
  weights/yolov8n.pt              # downloaded separately; may be bundled in ZIP
  data/drishti.sqlite3            # runtime, not part of source distribution
```

## 1. macOS installation, step by step

Use a Mac with Python **3.11**, Homebrew and at least a few GB of free space. Apple Silicon uses native arm64 Python; avoid mixing Rosetta and native libraries.

```bash
# Install Python and actual OCR executable/languages.
brew install python@3.11 tesseract tesseract-lang

cd drishti-ai-backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install/reuse official YOLO weights explicitly.
python scripts/download_models.py

# Verify OCR language packs. eng, hin and mar must be listed.
tesseract --list-langs

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the generated value into `.env` as `API_KEY=...`. Adjust `CORS_ORIGINS` to your actual React origin (e.g. `http://192.168.1.20:5173`). Do not use `*`.

```bash
python scripts/run_server.py
```

The server listens on `0.0.0.0:8000` so the phone can reach it. Allow incoming trusted-LAN connections in the macOS firewall if prompted.

Find the laptop's Wi-Fi IP with System Settings → Wi-Fi → Details → TCP/IP, or `ipconfig getifaddr en0` when Wi-Fi is en0. On the **phone**, use `http://LAPTOP_LAN_IP:8000`, not `localhost`.

## 2. Windows installation, step by step

Install Python 3.11 x64 from python.org (enable PATH) and Microsoft Visual C++ runtime if required. Install Tesseract with the English, Hindi (`hin`) and Marathi (`mar`) language data. Windows installers are linked from https://tesseract-ocr.github.io/tessdoc/Installation.html ; review installer provenance. `pytesseract` alone does not install the OCR executable.

PowerShell:

```powershell
cd drishti-ai-backend
py -3.11 -m venv .venv
# If activation is blocked, use .venv\Scripts\python.exe directly instead.
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# CPU-only PyTorch avoids downloading CUDA dependencies.
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python scripts/download_models.py
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set the generated secret in `.env`. If Tesseract is not on PATH, set this unquoted `.env` value:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

In its `tessdata` directory, verify `eng.traineddata`, `hin.traineddata`, `mar.traineddata`. Official language models: https://github.com/tesseract-ocr/tessdata_fast . Tesseract must be able to locate them; set `TESSDATA_PREFIX` if installed outside the standard location.

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
python scripts/run_server.py
ipconfig
```

Use the Wi-Fi IPv4 address from `ipconfig` in the Android app. Permit Python TCP 8000 on **Private networks only**, not unrestricted public networks. Same Wi-Fi SSID does not guarantee reachability: guest/client isolation can block connections.

## 3. Linux/CPU testing installation

```bash
sudo apt-get install python3.11-venv tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar libgl1 libglib2.0-0
python3.11 -m venv .venv
source .venv/bin/activate
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python scripts/download_models.py
cp .env.example .env
# Change API_KEY before network use.
python scripts/run_server.py
```

If Python 3.11 is not supplied by your distribution, install it through a trusted Python manager. Do not modify your system Python.

## 4. Configure and test the API

Swagger UI: `http://LAPTOP_IP:8000/docs`. Click **Authorize**, enter the `.env` API key, then test endpoints. `/openapi.json` provides the machine-readable schema. Data endpoints are authenticated; the static sender and API documentation contain no secrets.

Bash examples (substitute your real laptop address):

```bash
export BASE=http://192.168.1.20:8000
export KEY='the-value-from-your-backend-env'
curl -H "X-API-Key: $KEY" "$BASE/api/health"
curl -H "X-API-Key: $KEY" "$BASE/api/device/status"

curl -X POST -H "X-API-Key: $KEY" \
  -F 'image=@tests/fixtures/street.jpg;type=image/jpeg' \
  "$BASE/api/detection/analyze?language=hi&device_id=manual-test"

curl -X POST -H "X-API-Key: $KEY" \
  -F 'image=@tests/fixtures/ocr-mr.png;type=image/png' \
  "$BASE/api/ocr/read?language=mr"

curl -X POST -H "X-API-Key: $KEY" \
  -F 'image=@tests/fixtures/street.jpg;type=image/jpeg' \
  "$BASE/api/scene/describe?language=en"

curl -X POST -H "X-API-Key: $KEY" \
  -F 'image=@tests/fixtures/street.jpg;type=image/jpeg' \
  "$BASE/api/camera/frame?language=hi&device_id=my-android"

curl -H "X-API-Key: $KEY" "$BASE/api/detection/history?limit=20&offset=0"
curl -X DELETE -H "X-API-Key: $KEY" "$BASE/api/detection/history?device_id=manual-test"

curl -X POST -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"message":"सामने एक व्यक्ति है।","language":"hi","device_id":"manual-voice","priority":"high"}' \
  "$BASE/api/voice/message"
```

PowerShell can use `curl.exe` rather than its `curl` alias:

```powershell
$base='http://192.168.1.20:8000'
$key='your-api-key'
curl.exe -H "X-API-Key: $key" "$base/api/health"
curl.exe -H "X-API-Key: $key" -F "image=@tests/fixtures/street.jpg" "$base/api/detection/analyze?language=hi"
```

### Endpoint matrix

All image POSTs use `multipart/form-data`, field **`image`**, query `language=en|hi|mr` and optional validated `device_id`.

| Method | Endpoint | Actual behavior |
|---|---|---|
| GET | `/api/health` | Engine readiness; 200 JSON status may be `degraded` |
| POST | `/api/camera/frame` | Phone frame + YOLO/priority/tracking/history/broadcast |
| POST | `/api/detection/analyze` | YOLO on still image, no tracking claims |
| POST | `/api/detection/analyze-all` | YOLO + OCR + detected-object summary; errors if required OCR is unavailable |
| POST | `/api/ocr/read` | Real local OCR only; does not require YOLO |
| POST | `/api/scene/describe` | Detected-object summary only |
| POST | `/api/obstacle/detect` | Prioritized objects and cautious message |
| POST | `/api/navigation/guidance` | Observation, not turn-by-turn navigation |
| POST | `/api/voice/message` | JSON text → localized TTS metadata/cooldown; no audio file |
| GET | `/api/detection/history` | `records`, `total`, `limit`, `offset`; optional `device_id` |
| DELETE | `/api/detection/history` | Delete real SQLite events; optional `device_id` |
| GET | `/api/device/status` | Android heartbeat and actual supported model classes |
| WS | `/api/ws/vision` | Camera producer or dashboard observer |
| GET | `/api/camera/status` | Compatibility status heartbeat |
| GET | `/api/camera/snapshot` | Latest real JPEG plus `X-Drishti-Event-Id`; 409 when stale |
| GET | `/api/camera/stream` | Authenticated actual phone MJPEG; stops on expiry |
| POST | `/api/voice/command` | Status-only frontend compatibility adapter; not an LLM |

Image boxes are in the original decoded image coordinates returned as `width` and `height`. Confidence is **0–1**, not percentage. The React adapter converts it to display percentages. No confidence is invented. Empty detections are a valid result, not evidence of safety.

Success responses include ISO-8601 timestamp, event UUID, `detections`, `language`, `tts_locale`, `voice_message`, structured `voice`, warnings, timing and applicable `ocr`/`scene_description`. The exact schema is in `database/models.py` and `/docs`.

Errors use `{success:false,timestamp,error,code}`. Common statuses: 401 auth, 413 size, 415 format, 422 invalid image/parameters, 429 busy/rate-limit, 503 weights/OCR unavailable, 504 OCR timeout. On 429, **drop the old frame**, wait, and send a fresh one; do not build a queue.

## 5. Android native client — CameraX + native TTS

The `android/` directory contains a buildable-structured Android Studio project: Kotlin activity, CameraX preview/analyzer, permissions, OkHttp binary WebSocket, native TTS, rear camera selection, rotation, JPEG quality 70, 640px longest-side cap, one frame/sec, one outstanding frame, 45-second acknowledgement timeout and exponential reconnect. Images are not saved by this app. API keys remain in memory; only server URL, device UUID and language are saved in local preferences. Capture stops in the background.

**This source has not been compiled or device-tested here.** No Android SDK/emulator was available. Treat device validation as a required release gate, not as a completed test.

1. Install Android Studio, Android SDK 35 and JDK 17.
2. Open the `android` folder as a Gradle project. Use **Gradle 8.9**, Android Gradle Plugin 8.7.3, Kotlin 2.0.21. Android Studio can configure the Gradle distribution; no binary Gradle wrapper JAR is bundled. If you have Gradle 8.9 installed, run `gradle wrapper --gradle-version 8.9` inside `android/` to generate wrapper files, then `./gradlew assembleDebug` (Windows: `gradlew.bat assembleDebug`).
3. Sync and run the `app` module on a physical Android phone (API 26+).
4. Enter `http://LAPTOP_LAN_IP:8000` and the backend API key. For release builds, use trusted HTTPS/WSS.
5. Choose English / हिन्दी / मराठी, grant camera permission, and tap **Start Android rear camera**.
6. Install the matching language voice packs in Android Settings → Text-to-Speech. Some vendor engines do not provide all languages offline; the app reports missing packs rather than pretending to speak.
7. Open the React Live Vision screen on the laptop and select Start Camera to **view phone frames**. This button does not remotely turn on the phone camera.

Debug builds allow trusted local cleartext HTTP for development. Release builds disallow cleartext and require HTTPS. Do not ship debug network policy to users. Always verify TalkBack labels, orientation, thermal load, radio interruptions, TTS latency and battery behavior on actual hardware.

## 6. Browser camera fallback

Visit `https://YOUR_TRUSTED_HOST/camera-sender` on Android. Enter API key and start the camera. The browser uses the rear camera, 640px JPEG quality .7, one frame/sec and native browser speech synthesis. It refuses laptop/desktop capture.

**Phone browsers cannot access a camera at plain `http://192.168.x.x`**: `getUserMedia` requires a secure context. Use a trusted HTTPS reverse proxy or the native Android debug app. Another USB development option is `adb reverse tcp:8000 tcp:8000`, then open `http://localhost:8000/camera-sender` on the phone. This USB option is for debugging, not the Wi-Fi architecture.

The sender uses the origin it is served from, not a hardcoded phone localhost. If served through Vite, `/camera-sender` and `/api` are proxied together. Add the actual browser origin to `CORS_ORIGINS`; WebSocket origins are checked too. Do not log API keys in URLs; configuration sends keys in the first socket JSON message.

## 7. WebSocket protocol

Connect to `ws://LAPTOP_IP:8000/api/ws/vision` (WSS with TLS). Within ten seconds, send JSON:

```json
{"role":"camera","device_id":"my-android","language":"hi","mode":"obstacle","api_key":"YOUR_KEY"}
```

The server sends `type=ready`, then `type=camera_status`. Next send each JPEG as **one binary WebSocket message**, not base64. Wait for `type=detections` or an error before sending the next frame. Start at one frame/sec; server default maximum is two processed frames/sec. `mode` accepts `detection`, `obstacle`, `scene`, `all`. `all` additionally requires OCR and is slower.

Observers use:

```json
{"role":"watch","device_id":"laptop-dashboard","language":"en","api_key":"YOUR_KEY"}
```

Observers receive the latest result across connected phones and camera-status changes, not image binaries. Shared-key observers can see all devices: use proper tenant/device authorization before public/multi-user deployments. Voice payload language comes from the producing phone's selection. Restart/reconfigure the camera session after a language change. The React language selection controls still-image requests and browser speech settings.

Manual WebSocket protocol test without opening any camera:

```bash
python scripts/camera_upload_client.py --url ws://192.168.1.20:8000/api/ws/vision --key "$KEY" --image tests/fixtures/street.jpg --language hi
```

Frame freshness, not just an open socket, determines camera connectivity. Stale preview frames are discarded after `CAMERA_TIMEOUT` seconds. Snapshots carry the inference event ID; React only overlays boxes when the snapshot and detection event IDs match.

## 8. Connect the React frontend

The sibling `drishti-ai` has already been updated. From that folder:

```bash
npm install
cp .env.example .env
npm run dev
```

Local laptop `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_MODE=false
```

For phone-hosted frontend access, this localhost URL is **wrong**. Use `http://LAPTOP_LAN_IP:8000` in a native client, or HTTPS in a browser. For same-origin development, set `VITE_API_BASE_URL=` and let Vite proxy `/api` (including WebSockets) and `/camera-sender` to the laptop backend. The delivered workspace uses this proxy configuration. In production use an HTTPS same-origin reverse proxy; Vite's development proxy does not exist in static production hosting.

Open `/devices`, enter the API key from the backend `.env`, and select Apply API key. It is saved in **sessionStorage** and live observers reconnect automatically. The key is never compiled into a VITE variable. Tab-local storage does not constitute user authentication; shared device security and XSS still matter.

`src/services/api.js` maps actual API schemas to the existing UI, preserves raw response data, uses authenticated fetch and WebSocket, handles server errors, reconnects observers, adapts OCR and scenes, paginates the first 100 history events and supports real history deletion. APIs support further history pagination. The dashboard never fabricates a camera-connected state or battery percentage. Demo data remains available **only** when explicitly setting `VITE_DEMO_MODE=true`.

## 9. Tests and measured checks

```bash
# Run from backend folder after installing weights and language packs.
python -m pytest -q
```

19 tests passed in the development Linux/Python 3.11 environment. The suite covers actual YOLO calls, actual English OCR, actual Hindi/Marathi Devanagari fixtures, API auth/errors, SQLite roundtrip/delete, image size rejection, socket upload/observer, camera expiry, tracker IDs, evidence-bound summaries and cooldowns. Engine-dependent tests explicitly skip when dependencies are missing; no runtime fake detector is substituted.

`tests/fixtures/street.jpg` is an **AI-generated illustrative street image**, used as input to real inference. It is not a physical-world validation dataset. Do not treat detections on that fixture as a safety/accuracy benchmark. OCR fixtures are local rendered printed text.

In the sibling frontend folder, with both servers running:

```bash
node tests/integration.mjs
```

This local end-to-end test reads the sibling backend `.env` key, visits all routes, uploads a real input image to YOLO, checks actual OCR/scene/history, sends an Android-protocol REST frame, checks the WebSocket dashboard update and actual JPEG preview, and checks mobile overflow. This is not a physical Android test. The older `tests/smoke.mjs` is a demo-mode regression test; use it with `VITE_DEMO_MODE=true`, not against an empty real history database.

## 10. Performance and operations

- Run **one Uvicorn worker**. Multiple workers load multiple models, split in-memory phone state and broadcasts, and are unsupported without shared state/pubsub.
- The model loads once in lifespan. CPU detection/OCR/database work is offloaded from the event loop. A nonblocking global inference lock returns 429 instead of queuing stale work.
- `PROCESSING_FPS=2` is a maximum acceptance rate, not a guaranteed throughput. Start the phone at **one frame/sec** and measure actual `inference_ms`, network latency, TTS age and thermal behavior. OCR and initial inference can be slower.
- `CPU_THREADS=2` default prevents thread oversubscription. Tune only after measuring on the target laptop.
- Standard YOLO letterboxes/resizes for configured `INFERENCE_SIZE=640`; returned boxes map back to original dimensions. Tesseract scales within a bounded 1800px side.
- Upload bytes, decoded pixel count, dimensions, track/session count, active socket count, observer queue length and retained SQLite rows are bounded.
- `run_server.py` sets Uvicorn WebSocket max frame size and queue. Reverse proxies must also enforce HTTP upload size, timeouts and connection/rate limits.
- Optional CUDA: install compatible PyTorch from https://pytorch.org/get-started/locally/ and set `INFERENCE_DEVICE=0`. Optional compatible Mac acceleration: `INFERENCE_DEVICE=mps`, then validate operator support and quality. CPU remains the default; GPU acceleration was not tested here.
- SQLite uses WAL, parameterized queries and bounded retention. Each event stores detections, OCR and messages, not source images. Those records can still contain personal text: set retention, obtain informed consent and restrict disk access. Delete them through the authenticated API.

## 11. Security and safety release gates

This is not a publicly deployable, fully hardened service merely because the folder structure is production-oriented.

- Use a long random `API_KEY`, trusted Wi-Fi, explicit origins and HTTPS/WSS. Empty API keys are permitted only for deliberate isolated local development and emit a warning.
- Auth is a **shared-key local prototype**, not per-user/tenant authorization. Add identity, device permissions, key rotation, TLS termination, resource/rate limits, monitoring and dependency/security audits before public exposure.
- Origin/CORS checks are not authentication. Never expose an unprotected proxy that injects the server key for arbitrary users.
- The backend strips image metadata for in-memory preview and keeps only the freshest phone JPEG. No external AI calls are made. The optional browser TTS/recognition engine's own privacy policy is separate from this backend; use offline Android TTS when required.
- Do not enable verbose logs containing recognized private text or images. Application logs omit bodies and keys.
- Never announce a path is safe because the detector found nothing. Never decide road-crossing safety from YOLO. Traffic warnings are cautious, not permission to cross.
- Never infer exact distance or a child's age from a bounding box. Tracking and priorities are uncertain heuristics.
- Use a white cane, guide dog, orientation/mobility training or human assistance. Conduct usability, accessibility and hazard testing with informed participation before assistive use.

## Model/executable/license checklist

Separately install/review:
1. **YOLOv8n weights**: official Ultralytics download through `scripts/download_models.py`. Tested SHA256: `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`. The script prints a checksum for verification; it does not authenticate arbitrary user-supplied weights.
2. **Tesseract executable** plus **eng/hin/mar traineddata** (not included by pip).
3. **Python 3.11**, PyTorch, OS OpenCV runtime libraries as applicable.
4. **Android Studio/SDK/JDK/Gradle**, a physical Android phone and installed TTS languages. No compiled APK supplied.
5. **Optional custom-trained detector** for unsupported obstacles; validated depth model/calibration and a genuine local VLM only if you separately implement and validate those advanced capabilities.

Ultralytics code/weights have AGPL-3.0/enterprise licensing considerations. Review https://www.ultralytics.com/license and all dependency/model licenses before distributing a closed-source product. No blanket proprietary license is asserted for bundled dependencies or weights.

## Object-by-object voice + phone vibration revision

Actual detection responses now include:
- `object_announcements`: spoken object-name/position groups, with counts for repeated objects.
- `voice_pending_count`: groups not yet announced in this cycle.
- `haptic`: `{vibrate, pattern_ms, reason, meaning}`. Patterns are Android timing arrays (initial delay, vibration, pause, ...), not distance or safe-path signals.

YOLO-supported objects currently visible are announced in **fair batches of up to 4 distinct class/position groups**, prioritizing never-announced groups. Objects that remain visible are carried forward across accepted frames, not stored as a stale narration list. New positions can be announced. The same unchanged group is suppressed until `REPEAT_AFTER`; batches observe `ANNOUNCEMENT_COOLDOWN`. This does not promise that every physical object is recognized or that a fleeting detection will be spoken before it disappears.

Phone vibrations signal new/repositioned detected groups, with a two-second server cooldown and local debounce. High-priority detections use two short pulses, others use one. These mean **attention to a detection**, not collision certainty, proximity or permission to move. Repeated identical frames do not vibrate continuously.

Native Android source adds the VIBRATE permission, separate voice/vibration switches, Android Vibrator/VibratorManager support and a bounded non-overlapping TTS queue. Speech older than 12 seconds is discarded; do not build an unsafe backlog of old observations. Browser Android sender also has voice/vibration toggles; browser vibration is best-effort and may be unavailable or blocked by device/browser/user settings. The native source must be rebuilt/reinstalled to apply changes and remains **not compiled or physical-device tested here**.

Backend test suite now has **22 passing tests**, including all-group fair batching, repeated-object counting and haptic duplicate suppression. To try it, restart the backend and reconnect the phone sender. A single still-image response speaks at most one batch; send continuing camera frames for remaining currently visible groups.

### Frontend connection UI update

The current React Device Management screen includes **Backend URL**, **API key** and **Connect backend**. This runtime URL override takes precedence over the frontend env URL for that tab and applies without restarting Vite. Leave it empty for same-origin proxying. The header checks authenticated health every five seconds and distinguishes backend readiness from Android camera freshness. URL/key setup through the actual UI, tab persistence and real end-to-end inference were verified. Earlier references to an Apply API key button mean the current Connect backend button.
