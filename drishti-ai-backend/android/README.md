# Drishti Android camera client source

Open this folder in Android Studio. See the backend README for full setup. Required: JDK 17, Android SDK 35, Gradle 8.9, AGP 8.7.3, Kotlin 2.0.21 and a physical Android phone (API 26+). A binary Gradle wrapper JAR is not bundled; Android Studio can use a configured Gradle distribution. Alternatively, with Gradle 8.9 installed:

```bash
gradle wrapper --gradle-version 8.9
./gradlew assembleDebug
# Windows: gradlew.bat assembleDebug
```

No APK or physical-device validation is claimed. Build and test camera rotation/permissions, reconnection, TalkBack, selected TTS language availability and network behavior on target hardware.

Enter your laptop LAN URL and backend API key. Do not enter the phone's localhost. Choose a language and start the rear camera. Sends at most one outstanding compressed JPEG at one frame/sec, receives actual detection/voice JSON, and speaks with Android TextToSpeech. Stops capture in background. Debug permits trusted-LAN HTTP; release requires HTTPS and a trusted certificate. API key stays in memory, not preferences.

Never treat object detections as road-crossing permission or a safe-path guarantee. This is an assistive prototype, not a replacement for primary mobility aids.
