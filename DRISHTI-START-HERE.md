# Drishti — start here

## Delivered projects

1. **drishti-ai-backend/** — Python 3.11 FastAPI backend, real YOLOv8n/OpenCV, multilingual local Tesseract, SQLite history, Android WebSocket and REST camera upload, cautious multilingual voice messages.
2. **drishti-ai/** — existing premium React frontend, now connected to the real backend with API-key auth and live observer updates. Brand remains **Drishti**, without an AI suffix.
3. **drishti-ai-backend/android/** — native Android CameraX + OkHttp + TextToSpeech source project. No compiled APK; Android build/device validation is still required.

## Read these instructions first

The backend's **README.md** contains complete step-by-step **macOS and Windows installation**, model/OCR downloads, Wi-Fi/firewall troubleshooting, API testing commands, Android setup, security settings and precise capability limits.

### Backend quick start

```bash
cd drishti-ai-backend
python3.11 -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/download_models.py
# Install the actual Tesseract executable and eng/hin/mar language packs separately.
cp .env.example .env
# Windows instead: Copy-Item .env.example .env
# Set a long random API_KEY and trusted CORS_ORIGINS in .env.
python scripts/run_server.py
```

`python3.11` on Windows is normally `py -3.11`. For Windows/Linux CPU-only PyTorch, follow the backend README's CPU-index install commands to avoid unnecessary CUDA downloads.

Open backend `/docs`, authorize with the API key, then test an image upload. YOLO weights are included in the combined source archive for convenience; the download script reuses an existing file and prints its hash. Review model licensing before distribution. Python environments, OCR executables/language packs, node_modules, Android SDK/Gradle, private .env files and personal runtime database files are **not** bundled.

### Frontend quick start

```bash
cd drishti-ai
npm install
cp .env.example .env
npm run dev
```

For laptop-local development use `VITE_API_BASE_URL=http://localhost:8000`. For same-origin development leave it empty and Vite proxies `/api` and `/camera-sender`. For a phone/browser on another device, use a reachable laptop LAN URL or trusted HTTPS hostname, never the phone's localhost. Production static hosting requires its own API/WebSocket reverse proxy.

In **Device Management**, enter the same backend API key. It is stored in tab-local sessionStorage, not compiled into the frontend. Applying it reconnects live updates.

### Android camera

Open `drishti-ai-backend/android/` in Android Studio. Use JDK 17, SDK 35 and Gradle 8.9. Build and run on a physical Android phone (API 26+), enter the laptop LAN URL/API key, choose a voice language and start the rear camera. The laptop's camera is never opened. The browser sender is an optional Android-only HTTPS fallback at backend `/camera-sender`.

## Verification performed

- **22 backend tests passed**, with actual YOLO and actual English/Hindi/Marathi Tesseract OCR.
- React production build passed.
- End-to-end browser test passed across 13 routes, real uploads, OCR, detected-object scene summary, SQLite history, phone-protocol frame upload, WebSocket update, actual JPEG preview and mobile overflow checks.
- Warm repeated CPU still-image processing on the illustrative test image: 71–81 ms over five measured requests (median 72.67 ms). This is not a hardware guarantee or phone-to-speech latency benchmark.
- **Not performed:** native Android compilation, physical-phone camera/network/TTS tests, GPU tests, real-world hazard/accuracy benchmark or safety certification.

## Safety and scope

Distances are always unavailable without a validated depth method. Scene descriptions summarize only detected objects; no detailed VLM is included. No actual GPS routing, safe-path decision or safe-road-crossing decision is implemented. Default YOLO does not support every obstacle class. Native Android TTS and camera behavior must be checked on a real phone before use.

Assistive prototype only. Never replace a white cane, guide dog, mobility training or human assistance. Authentication is a shared-key local-development approach, not public multi-user production security. Add TLS, per-device authorization, rate limiting, privacy controls and independent safety/accessibility validation before deployment.

## Voice and vibration update

Detected object groups now receive fair batched voice announcements and new-detection haptic payloads. Native Android and the Android browser sender have independent voice/vibration toggles. Rebuild/install the updated native source or refresh/reconnect the browser sender. Vibration is device/browser dependent; physical Android validation is still required.
