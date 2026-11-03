# JARVIS: Production-Ready Windows AI Desktop Assistant

An elite, modular, event-driven AI Desktop Assistant built specifically for **Windows 10 & 11**.

JARVIS combines real-time voice interaction, long-term memory, system automation, multimodal vision, web intelligence, and multi-step workflow automation with seamless offline resilience.

---

## 🚀 Key Capabilities

- **🎙️ Voice Interface & Wake-Word**: Continuous listening with wake-word detection ("Jarvis", "Hey Jarvis"), Windows SAPI5 Text-to-Speech, and conversational turn management.
- **🧠 Hybrid AI Reasoning**: Powered by Google Gemini 2.5 Flash and OpenAI/Ollama, with deterministic offline fallback when disconnected from the internet.
- **💾 Long-Term Memory & Context**: Persistent SQLite database (WAL mode) tracking conversation history with token budgeting, user preferences, notes, and scheduled reminders.
- **🖥️ Windows System Automation**: Native Win32 control over open windows (focus, minimize, maximize, close), volume, media playback, workstation lock, and application launching.
- **📊 Real-Time Hardware Monitoring**: Zero-dependency ctypes queries for CPU load, RAM usage, C: drive disk space, battery status, and process termination.
- **👁️ Computer Vision & OCR**: Desktop screenshot capture, region extraction, base64 multimodal vision analysis, and text extraction.
- **📋 Clipboard & File Management**: Searchable clipboard history, file content read/write, fast search, automated directory categorization, and SHA-256 integrity checks.
- **🌐 Web Intelligence**: Real-time web search (DuckDuckGo), encyclopedic lookups (Wikipedia), and live weather forecasts.
- **⚙️ Multi-Step Workflows & Macros**: Pipeline automation engine with variable propagation (`${var}`), conditional execution, and audit logging.
- **🔌 Dynamic Plugin Architecture**: Drop-in plugin loader enabling new tools and event listeners without modifying core code.
- **🌐 FastAPI REST & WebSocket Server**: Built-in HTTP and WebSocket interface ready for custom desktop dashboards, electron sidecars, or mobile clients.

---

## 📂 Project Structure

```
jarvis ai agent desktop/
├── jarvis/
│   ├── automations/windows/     # Window control, volume, media, app launcher, power
│   ├── brain/                   # Gemini, OpenAI, Offline intent engine, Router
│   ├── core/                    # Config (Pydantic), EventBus, Logger, Context
│   ├── memory/                  # SQLite WAL database, Conversation & Semantic stores
│   ├── monitoring/              # Native Win32 CPU, RAM, Disk, Battery, Processes
│   ├── plugins/                 # Base plugin contract, dynamic loader
│   ├── tools/                   # File manager, Web search, Productivity, Developer
│   ├── ui/                      # Interactive Rich CLI, FastAPI REST/WebSocket server
│   ├── vision/                  # Screen capture, OCR, Vision analyzer
│   ├── voice/                   # Wake-word detector, STT, SAPI5 TTS, Voice listener
│   ├── workflow/                # Multi-step automation engine, Predefined routines
│   └── main.py                  # Unified application bootstrapper
├── plugins/                     # Drop-in user plugins (e.g. CalculatorPlugin)
├── tests/                       # Complete 48-test verification suite
├── ARCHITECTURE.md              # Deep architectural specification
├── .env.example                 # Configuration template
└── README.md                    # System documentation
```

---

## ⚡ Quick Start

### 1. Launch the Futuristic Web Dashboard (Recommended)
Simply double click [**`START_JARVIS.bat`**](file:///c:/jarvis%20ai%20agent%20desktop/START_JARVIS.bat) or run:
```powershell
python -m jarvis.main --mode web
```
This automatically boots all subsystems and opens the interactive Iron Man Arc Reactor dashboard at **`http://127.0.0.1:8765/`** in your default web browser!

### 2. Voice Commands on the Webpage
- **Click the Arc Reactor** or press **<kbd>Spacebar</kbd>** anywhere on the page to talk.
- Speak naturally: *"Open Notepad"*, *"What is my battery level?"*, *"Volume up"*, *"Take a note: Buy groceries"*.
- JARVIS speaks back with real-time text-to-speech, animates the Arc Reactor frequency visualizer, and executes Windows actions.
- Background desktop wake-word listening (`"Jarvis"`) is also active simultaneously!

### 3. Alternative CLI Mode
Start JARVIS in terminal mode:
```powershell
python -m jarvis.main --mode cli
```

---

## 💬 Example Commands & Interactions

### System & Windows Control
- `"Jarvis, open Notepad"`
- `"Jarvis, what is my battery level?"`
- `"Jarvis, check RAM memory usage"`
- `"Jarvis, check disk space on C:"`
- `"Jarvis, minimize Chrome"`
- `"Jarvis, volume up"`
- `"Jarvis, mute audio"`
- `"Jarvis, lock my computer"`
- `"Jarvis, take a screenshot"`

### Productivity & Memory
- `"Jarvis, remember that my favorite browser is Chrome"`
- `"Jarvis, take a note: buy groceries tomorrow"`
- `"Jarvis, remind me in 30 minutes to drink water"`
- `"Jarvis, list my notes"`
- `"Jarvis, text Alex on whatsapp: hello there"`
- `"Jarvis, what is on my clipboard?"`
- `"Jarvis, organize downloads"`

### Web, Developer & Automations
- `"Jarvis, what is the weather in New York?"`
- `"Jarvis, search Wikipedia for Quantum Computing"`
- `"Jarvis, play believer on YouTube"`
- `"Jarvis, check git status"`
- `"Jarvis, run morning briefing"`
- `"Jarvis, start focus mode"`
- `"Jarvis, calculate sqrt(144) + 25 * 4"`

---

## 🧪 Running the Test Suite

Run the full end-to-end verification suite covering all 9 phases:
```powershell
python -u tests/run_tests.py
```
*(Comprehensive unit and integration test suite covering core, memory, Win32 automations, brain routing and offline intent engine, voice listener, productivity tools, vision/OCR, dynamic plugins, and FastAPI REST/WebSocket endpoints).*

---

## 📄 License
MIT License. Built for production Windows desktop environments.
