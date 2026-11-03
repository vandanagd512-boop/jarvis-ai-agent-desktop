# JARVIS Architecture Specification

JARVIS is designed according to clean architecture, SOLID principles, and an asynchronous event-driven core tailored for Windows 10 & 11 environments.

---

## 1. Architectural Overview

```
                      +-----------------------------------+
                      |      User Interfaces (UI Layer)   |
                      |  - Interactive Terminal (Rich)    |
                      |  - Continuous Voice Listener      |
                      |  - FastAPI REST / WebSocket Server|
                      +-----------------+-----------------+
                                        |
                                        v
                      +-----------------+-----------------+
                      |     Reasoning & Brain Router      |
                      |  - Gemini 2.5 Flash Provider      |
                      |  - OpenAI / Local LLM Provider    |
                      |  - Offline Intent Engine          |
                      +---+-------------+---------------+--+
                          |             |               |
             +------------+             v               +------------+
             v                   Asynchronous                        v
     +---------------+            Event Bus                  +---------------+
     | Memory Layer  |         (Core Pub/Sub)                | Tool Registry |
     | - SQLite WAL  |    [Typed System Events]              | - Win32 APIS  |
     | - Conv Store  |                  |                    | - Automations |
     | - Facts & Pref|                  v                    | - Plugins     |
     | - Reminders   |          +---------------+            | - Workflows   |
     +---------------+          | System State  |            +---------------+
                                | & Context     |
                                +---------------+
```

---

## 2. Core Subsystems

### 2.1 Core Foundation (`jarvis/core/`)
- **`config.py`**: Pydantic Settings with dynamic resolution of directories, database connection strings, and fallback parameters.
- **`events.py`**: Asynchronous EventBus enabling zero-coupling event distribution across subsystems (`publish`, `publish_sync`, `subscribe`, `unsubscribe`).
- **`logger.py`**: Dual-target logging featuring Rich terminal formatting with auto-rotation file handler (10MB limit with 5 backups).
- **`context.py`**: Real-time snapshot of foreground window title, battery level, hardware usage, and user state.

### 2.2 Memory & Persistence (`jarvis/memory/`)
- **`database.py`**: SQLite engine initialized with `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` ensuring ultra-low latency concurrent reads/writes.
- **`models.py`**: SQLAlchemy schema for `Conversation`, `Message`, `UserFact`, `Note`, `Reminder`, and `ExecutionAuditLog`.
- **`conversation_store.py`**: Multi-turn dialogue persistence with token budgeting to prevent context overflow.
- **`semantic_store.py`**: Long-term declarative knowledge and preference recall using token-overlap ranking.

### 2.3 Reasoning & Brain (`jarvis/brain/`)
- **`router.py`**: Dynamic action dispatcher. Attempts primary cloud LLM (Gemini or OpenAI). If network fails or quota is exhausted, transparently falls back to `OfflineProvider` without user disruption.
- **`offline_provider.py`**: Deterministic rule and regex intent engine capable of executing system commands, app launches, media controls, notes, and diagnostics 100% offline.
- **`gemini_provider.py`**: Modern Google GenAI implementation with function calling and multimodal vision support.
- **`openai_provider.py`**: OpenAI-compatible client supporting cloud and local inference servers (Ollama, LM Studio).

### 2.4 Windows Native Automations (`jarvis/automations/windows/`)
- **Zero external psutil dependency**: Pure Win32 ctypes implementation for hardware metrics (`GlobalMemoryStatusEx`, `GetDiskFreeSpaceExW`, `GetSystemTimes`, `GetSystemPowerStatus`).
- **`window_manager.py`**: Native `user32` window finding, focusing, restoring, minimizing, maximizing, and closing.
- **`media_controls.py`**: Virtual key events for system volume, mute toggle, play/pause, next/previous tracks.
- **`power_manager.py`**: Safe workstation lock, sleep, and timed shutdown with abort capability.
- **`app_launcher.py`**: Process spawning with detached process groups and Windows Shell protocol URI handling.

### 2.5 Voice & Audio Subsystem (`jarvis/voice/`)
- **`tts.py`**: Background worker queue driving Windows SAPI5 (`pyttsx3`) with graceful console fallback.
- **`stt.py`**: Audio stream listener using `speech_recognition` with dynamic ambient noise calibration.
- **`wake_word.py`**: Regex and phonetic pattern matcher extracting trailing commands directly from wake-word utterances.
- **`listener.py`**: 4-state finite state machine (`SLEEPING` -> `LISTENING` -> `THINKING` -> `SPEAKING`).

### 2.6 Productivity, Vision & Web Tools (`jarvis/tools/`, `jarvis/vision/`)
- **`file_ops.py`**: Fast glob searches, file content read/write, automated download/desktop organizer, and SHA-256 hashing.
- **`web_search.py`**: DuckDuckGo API, Wikipedia summaries, and real-time weather reports without API keys.
- **`code_runner.py`**: Isolated Python and PowerShell execution sandbox with timeout enforcement.
- **`screen_capture.py`**: High-performance multi-monitor screenshot capture and base64 multimodal encoding.
- **`clipboard_manager.py`**: Real-time clipboard audit trail with search and fallback buffer.

### 2.7 Extensible Plugins & Workflows (`jarvis/plugins/`, `jarvis/workflow/`)
- **`plugin_manager.py`**: Dynamic drop-in plugin discovery in `plugins/`. Plugins inherit `BasePlugin` and inject new tools and event listeners at runtime.
- **`workflow_engine.py`**: Multi-step pipeline execution engine supporting variable substitution (`${var}`), condition evaluation, and execution audit logging.

---

## 3. Reliability & Security Guarantees
1. **Offline Resilience**: Offline deterministic intent parser ensures critical desktop commands always execute even without internet.
2. **Crash Prevention**: All tool invocations and LLM network requests are wrapped with domain exception boundaries and event bus notifications.
3. **Audit Trail**: Every workflow step and sensitive automation is recorded in `execution_audit_logs`.
