# Drishti — React frontend

Premium responsive Drishti landing page and ten-screen accessibility dashboard, plus Help Center/Profile. React, Vite, JavaScript, React Router, Lucide, DM Sans/Manrope. Complete backend and native Android camera starter are supplied in the sibling `drishti-ai-backend` project.

## Start

Node.js 20.19+ / 22.12+:

```bash
npm install
cp .env.example .env
npm run dev
```

`npm run build` creates a static production bundle. Configure SPA fallback to `index.html`, and a same-origin backend/WebSocket reverse proxy when deploying.

## Real backend integration

The app is in **live mode by default**, not demo mode. Start the sibling Python backend first; see its detailed README for macOS/Windows setup, weights, OCR packs, security and Android instructions.

```env
# Local laptop browser only; not the phone's localhost.
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_MODE=false
```

For same-origin development set `VITE_API_BASE_URL=`. Vite proxies `/api` (including WebSockets) and `/camera-sender` to the laptop's port 8000. This is the delivered workspace configuration. On mobile, use a reachable backend LAN IP or HTTPS host, not a hardcoded localhost. In production use HTTPS/WSS and an actual reverse proxy; Vite's proxy is development-only.

Open `/devices` and enter the backend `.env` API key. It stays in tab-local sessionStorage; API requests use `X-API-Key`, and WebSockets send the key in their first configuration message. Applying a key reconnects the observer. No secret is compiled into VITE variables.

The **Android phone is the primary camera**. Start capture on the phone. The dashboard's Start Camera button views incoming phone frames and does not open a laptop webcam or remotely activate a phone camera. Phone snapshots are fetched with auth; boxes overlay only a matching frame/inference event ID.

`src/services/api.js` provides real detection, OCR, scene, obstacle, guidance, history/delete, device, voice and camera adapters; backend errors are surfaced in the UI. Live observations use `/api/ws/vision` with reconnect and latest-only server queues. OCR and scene responses are adapted to existing UI. Fractional confidence becomes percentage only for display. Distance is `Not available` unless supplied by a validated future method.

## Honest boundaries

- No fake live detections or hardware telemetry. Source images are illustrative only on the marketing page or in explicit demo mode.
- The model detects only its supported classes. Scene output is a detected-object summary, not a VLM-generated interpretation.
- The backend supplies no depth/distance estimation or GPS routing. The map is labeled illustrative. The Navigation screen can request actual image-based guidance separately.
- Native Android TextToSpeech is in the backend's `android/` source; the dashboard uses browser speech synthesis. Microphone recognition depends on browser/permission and has a text-command alternative.
- Language controls select English/Hindi/Marathi backend inference/voice languages; UI copy is English, not fully translated.
- History displays detections from the latest 100 stored events, with search/filter/export/delete. Backend APIs support further pagination.
- Explicit `VITE_DEMO_MODE=true` enables labeled demonstration data; it is not a fallback after a backend error.

## Routes

`/` landing, `/dashboard`, `/live-vision`, `/object-detection`, `/ocr-reader`, `/scene-understanding`, `/navigation`, `/voice-assistant`, `/history`, `/devices`, `/settings`, `/help`, `/profile`.

## Structure

```
src/components/  CameraPreview, VoiceAssistant, UI primitives
src/layouts/     DashboardLayout, Sidebar, Header
src/pages/       Landing, Overview, feature screens, DeviceManagement, DetectionHistory
src/context/     shared state, voice feedback and preferences
src/hooks/       reconnecting live observer lifecycle
src/services/    authenticated API and schema normalization
src/styles/      base, reference-matched dashboard and landing styling
```

## Accessibility

Semantic page regions, labeled controls, switch semantics, visible keyboard focus, skip links, status announcements, reduced motion, large text/high contrast, minimum 44px primary touch controls and saved preferences. Test with real screen readers and target devices before assistive deployment. No accessibility or safety certification is claimed.

## Tests

With backend running and `.env` API key configured:

```bash
npx playwright install --with-deps chromium
node tests/integration.mjs
```

This development test reads the sibling backend `.env`, visits all routes, tests real inference/OCR/scene/history, phone-frame upload/live results and mobile overflow. The older `tests/smoke.mjs` checks labeled demo behavior and should run with `VITE_DEMO_MODE=true`.

## Assets

Brand: **Drishti**, without an AI suffix. Selected blue smart-glasses/cyan sparkle wordmark is used in the header/sidebar/footer. Product and hero images are AI-generated illustrative marketing imagery. `public/street-reference.jpg` is an AI-generated illustrative camera sample; backend tests use it as input for actual inference, not as a real-world safety dataset. Original earlier crosswalk photo attribution: https://unsplash.com/photos/people-cross-a-busy-city-intersection-at-a-crosswalk-6SA2PY0eqMY . Google Fonts have system fallbacks.

## Safety

Assistive prototype only. Never infer a safe path, road-crossing permission or exact distance from these detections. Continue using a white cane, guide dog, mobility training or human assistance. Secure APIs and handle recognized private text responsibly before use outside trusted development Wi-Fi.

## Runtime connection setup

Device Management now provides Backend URL + API key + **Connect backend**. An empty URL uses the same-origin proxy. A custom URL must be an origin only (no path/credentials) and must use HTTPS when the frontend is HTTPS. Changes apply immediately and remain tab-local. The header reports actual authenticated `/api/health` status separately from camera connectivity. Entering a valid API key through this UI, reconnecting the WebSocket and reloading with tab-persistent configuration were browser-tested. CORS must allow the frontend origin on the chosen backend.
