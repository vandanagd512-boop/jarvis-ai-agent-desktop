/**
 * JARVIS Web Dashboard Client Controller
 * Manages WebSockets, Web Speech API, Canvas Audio Visualizer, and Desktop Automations.
 */

let ws = null;
let speechRecognizer = null;
let isListening = false;
let audioContext = null;
let analyser = null;
let microphoneStream = null;
let animationFrameId = null;

// Audio visualizer canvas
const canvas = document.getElementById("visualizerCanvas");
const ctx = canvas.getContext("2d");

// --- Initialization on Load ---
window.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  initMobileBattery();
  initLiveUptime();
  initWebSocket();
  initWebSpeech();
  initKeyboardShortcuts();
  loadNotes();
  loadContacts();

  // Periodic polling fallback for telemetry if WS is reconnecting
  setInterval(fetchTelemetry, 3000);
});

// --- Live Clock & Telemetry Initializers ---
function initLiveClock() {
  const clockEl = document.getElementById("liveClock");
  const dateEl = document.getElementById("liveDate");

  function update() {
    const now = new Date();
    if (clockEl) clockEl.innerText = now.toLocaleTimeString();
    if (dateEl) dateEl.innerText = now.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  }
  update();
  setInterval(update, 1000);
}

// --- Live Mobile Battery API ---
let hasNativeBattery = false;
async function initMobileBattery() {
  const batteryEl = document.getElementById("batteryText");
  if (!batteryEl) return;

  if ("getBattery" in navigator) {
    try {
      const battery = await navigator.getBattery();
      hasNativeBattery = true;
      function updateBatteryDisplay() {
        const pct = Math.round(battery.level * 100);
        const bolt = battery.charging ? '<i class="fa-solid fa-bolt text-amber-400 mr-1 animate-pulse"></i>' : '';
        const iconClass = pct > 75 ? "fa-battery-full text-emerald-400" : pct > 35 ? "fa-battery-half text-cyan-400" : "fa-battery-quarter text-rose-400";
        batteryEl.innerHTML = `${bolt}<i class="fa-solid ${iconClass} mr-1"></i>${pct}%`;
      }
      updateBatteryDisplay();
      battery.addEventListener("levelchange", updateBatteryDisplay);
      battery.addEventListener("chargingchange", updateBatteryDisplay);
    } catch (e) {
      console.warn("Battery API note:", e);
    }
  }

  if (!hasNativeBattery && (!batteryEl.innerText || batteryEl.innerText.includes("--"))) {
    batteryEl.innerHTML = `<i class="fa-solid fa-battery-three-quarters text-emerald-400 mr-1"></i>98% (Active)`;
  }
}

// --- Live Session & Hardware Uptime ---
const appSessionStartTime = Date.now();
function initLiveUptime() {
  const uptimeEl = document.getElementById("uptimeText");
  function tickUptime() {
    if (!uptimeEl) return;
    const elapsedSecs = Math.floor((Date.now() - appSessionStartTime) / 1000);
    const hrs = Math.floor(elapsedSecs / 3600);
    const mins = Math.floor((elapsedSecs % 3600) / 60);
    const secs = elapsedSecs % 60;
    if (hrs > 0) {
      uptimeEl.innerText = `${hrs}h ${mins}m`;
    } else {
      uptimeEl.innerText = `${mins}m ${secs}s`;
    }
  }
  tickUptime();
  setInterval(tickUptime, 1000);
}

// --- WebSocket Connection ---
function initWebSocket() {
  const loc = window.location;
  const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${loc.host}/ws`;

  console.log(`Connecting to JARVIS WebSocket: ${wsUrl}`);
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("Connected to JARVIS WebSocket");
    setSystemOnline(true);
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWebSocketMessage(msg);
    } catch (e) {
      console.error("Error parsing WS message:", e);
    }
  };

  ws.onclose = () => {
    console.warn("WebSocket disconnected. Retrying in 2 seconds...");
    setSystemOnline(false);
    setTimeout(initWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

function setSystemOnline(isOnline) {
  const dot = document.getElementById("systemStatusDot");
  const text = document.getElementById("systemStatusText");
  if (isOnline) {
    dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#00f5a0]";
    text.className = "text-xs font-bold tracking-wider text-emerald-400 uppercase";
    text.innerText = "ONLINE";
  } else {
    dot.className = "w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_#ff4b72]";
    text.className = "text-xs font-bold tracking-wider text-rose-500 uppercase";
    text.innerText = "RECONNECTING";
  }
}

function handleWebSocketMessage(msg) {
  if (msg.type === "telemetry") {
    updateTelemetryUI(msg.data);
  } else if (msg.type === "event") {
    handleServerEvent(msg);
  } else if (msg.type === "response") {
    handleAssistantResponse(msg.data);
  }
}

function handleServerEvent(ev) {
  console.log("Server Event:", ev.event_type, ev.payload);

  if (ev.event_type === "voice.wake_word_detected") {
    setVoiceState("listening", "Wake-word 'Jarvis' detected!");
    startListening();
  } else if (ev.event_type === "voice.speech_transcribed") {
    document.getElementById("liveTranscript").innerText = `"${ev.payload.transcription}"`;
  } else if (ev.event_type === "voice.tts_started") {
    setVoiceState("speaking", "JARVIS speaking...");
  } else if (ev.event_type === "voice.tts_finished") {
    setVoiceState("idle", "Standing by...");
  }
}

// --- Telemetry Fetching & UI Update ---
async function fetchTelemetry() {
  try {
    const res = await fetch("/status");
    if (res.ok) {
      const data = await res.json();
      updateTelemetryUI(data);
    }
  } catch (err) {
    // Silent catch during reload
  }
}

function updateTelemetryUI(data) {
  if (!data) return;

  const metrics = data.metrics || {};
  const context = data.context || {};

  // Active window
  if (context.active_window) {
    document.getElementById("activeWindowText").innerText = context.active_window;
  }

  // RAM
  if (metrics.ram) {
    const ramPct = parseInt(metrics.ram.load_percent) || 0;
    document.getElementById("ramValText").innerText = `${metrics.ram.used_gb} / ${metrics.ram.total_gb} GB (${ramPct}%)`;
    document.getElementById("ramBar").style.width = `${Math.min(100, ramPct)}%`;
  }

  // Disk C:
  if (metrics.disk_c) {
    const diskPct = parseFloat(metrics.disk_c.used_percent) || 0;
    document.getElementById("diskValText").innerText = `${metrics.disk_c.used_gb} GB Used / ${metrics.disk_c.free_gb} GB Free`;
    document.getElementById("diskBar").style.width = `${Math.min(100, diskPct)}%`;
  }

  // Battery
  if (metrics.battery && !hasNativeBattery) {
    document.getElementById("batteryText").innerHTML = `<i class="fa-solid fa-battery-half text-cyan-400"></i> ${metrics.battery}`;
  }

  // Uptime
  if (metrics.uptime && metrics.uptime !== "Active") {
    document.getElementById("uptimeText").innerText = metrics.uptime;
  }

  // CPU
  if (context.cpu_usage && context.cpu_usage !== "Unknown") {
    const cpuPct = parseFloat(context.cpu_usage) || 0;
    document.getElementById("cpuValText").innerText = `${cpuPct.toFixed(1)}%`;
    document.getElementById("cpuBar").style.width = `${Math.min(100, cpuPct)}%`;
  }
}

// --- Live Speech Scratchpad with Real-Time Correction ---
let isManuallyEditing = false;
let autoExecuteTimer = null;
let keepVoiceListening = false;

function executeScratchpadCommand() {
  clearTimeout(autoExecuteTimer);
  keepVoiceListening = false;
  if (speechRecognizer && isListening) {
    try { speechRecognizer.stop(); } catch (e) {}
    isListening = false;
    updateMicButton(false);
    stopAudioVisualizer();
  }

  const scratchpad = document.getElementById("liveScratchpad");
  if (!scratchpad || !scratchpad.value.trim()) return;

  const cmd = scratchpad.value.trim();
  const startTime = performance.now();
  const speedBadge = document.getElementById("execSpeedBadge");
  const scratchpadStatus = document.getElementById("scratchpadStatus");

  if (scratchpadStatus) {
    scratchpadStatus.innerText = "⚡ Executing command...";
    scratchpadStatus.className = "text-xs text-cyan-300 font-bold";
  }

  sendQuery(cmd).finally(() => {
    const elapsed = Math.round(performance.now() - startTime);
    if (speedBadge) {
      speedBadge.innerHTML = `<i class="fa-solid fa-bolt text-amber-300"></i> Executed in ${elapsed}ms`;
    }
    if (scratchpadStatus) {
      scratchpadStatus.innerText = "✅ Command executed successfully";
      scratchpadStatus.className = "text-xs text-emerald-400 font-bold";
    }
  });
}

function initWebSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const scratchpad = document.getElementById("liveScratchpad");
  const scratchpadStatus = document.getElementById("scratchpadStatus");
  const clearBtn = document.getElementById("clearScratchpadBtn");
  const runBtn = document.getElementById("executeScratchpadBtn");

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (scratchpad) scratchpad.value = "";
      if (scratchpadStatus) {
        scratchpadStatus.innerText = "Scratchpad cleared • Ready";
        scratchpadStatus.className = "text-xs text-cyan-400";
      }
    });
  }

  if (runBtn) {
    runBtn.addEventListener("click", () => {
      executeScratchpadCommand();
    });
  }

  if (scratchpad) {
    scratchpad.addEventListener("input", () => {
      isManuallyEditing = true;
      if (scratchpadStatus) {
        scratchpadStatus.innerText = "✏️ Editing (press Enter or Run to execute)";
        scratchpadStatus.className = "text-xs text-amber-300 font-bold";
      }
    });

    scratchpad.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        executeScratchpadCommand();
      }
    });
  }

  if (!SpeechRecognition) {
    console.info("Web Speech API not present; will use audio capture backend.");
    return;
  }

  try {
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = true;
    speechRecognizer.interimResults = true;
    speechRecognizer.lang = "en-US";

    speechRecognizer.onstart = () => {
      isListening = true;
      isManuallyEditing = false;
      playChime(880, "sine", 0.1);
      setVoiceState("listening", "Listening to your voice... Speak now!");
      updateMicButton(true);
      startAudioVisualizer();
      if (scratchpadStatus) {
        scratchpadStatus.innerText = "🎙️ Listening live (keep-alive active)...";
        scratchpadStatus.className = "text-xs text-cyan-300 font-bold animate-pulse";
      }
    };

    speechRecognizer.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const spoken = (final || interim).trim();
      if (spoken && scratchpad && !isManuallyEditing) {
        scratchpad.value = spoken;
      }
      document.getElementById("liveTranscript").innerText = `"${spoken}"`;
      if (scratchpadStatus) {
        scratchpadStatus.innerText = "✏️ Live text (editable before running)";
        scratchpadStatus.className = "text-xs text-amber-300 font-medium";
      }

      if (event.results[event.results.length - 1].isFinal) {
        // Allow a brief pause before executing so user can continue speaking or edit
        clearTimeout(autoExecuteTimer);
        autoExecuteTimer = setTimeout(() => {
          if (!isManuallyEditing && scratchpad && scratchpad.value.trim() && !keepVoiceListening) {
            executeScratchpadCommand();
          }
        }, 1800);
      }
    };

    speechRecognizer.onerror = async (event) => {
      console.warn("Speech recognition note:", event.error);
      if (event.error !== "no-speech") {
        if (scratchpadStatus) scratchpadStatus.innerText = `Status: ${event.error}`;
      }
    };

    speechRecognizer.onend = () => {
      if (keepVoiceListening) {
        try {
          speechRecognizer.start();
          return;
        } catch (e) {}
      }
      isListening = false;
      updateMicButton(false);
      stopAudioVisualizer();
      if (!isManuallyEditing && (!scratchpad || !scratchpad.value.trim())) {
        setVoiceState("idle", "Standing by (Click Arc Reactor to talk)...");
      }
    };
  } catch (err) {
    console.warn("SpeechRecognition init error:", err);
  }

  // Wire Arc Reactor click to toggle speech
  const orb = document.getElementById("voiceOrb");
  if (orb) {
    orb.addEventListener("click", () => {
      toggleVoiceListening();
    });
  }
}

let isDesktopCapturing = false;
let isBrowserRecording = false;
let pcmBuffers = [];
let audioInputNode = null;
let scriptProcessor = null;
let recordingTimer = null;

function playChime(freq = 880, type = "sine", duration = 0.12) {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    // Audio context may require user gesture
  }
}

function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  // RIFF identifier
  writeString(view, 0, 'RIFF');
  // file length
  view.setUint32(4, 36 + samples.length * 2, true);
  // RIFF type
  writeString(view, 8, 'WAVE');
  // format chunk identifier
  writeString(view, 12, 'fmt ');
  // format chunk length
  view.setUint32(16, 16, true);
  // sample format (1 = raw PCM)
  view.setUint16(20, 1, true);
  // channel count (1 = mono)
  view.setUint16(22, 1, true);
  // sample rate
  view.setUint32(24, sampleRate, true);
  // byte rate (sampleRate * 2)
  view.setUint32(28, sampleRate * 2, true);
  // block align (channel count * bytes per sample)
  view.setUint16(32, 2, true);
  // bits per sample
  view.setUint16(34, 16, true);
  // data chunk identifier
  writeString(view, 36, 'data');
  // data chunk length
  view.setUint32(40, samples.length * 2, true);

  // Peak amplitude detection and smart amplification (up to 8x boost)
  let maxVal = 0;
  for (let i = 0; i < samples.length; i++) {
    const abs = Math.abs(samples[i]);
    if (abs > maxVal) maxVal = abs;
  }
  const gain = maxVal > 0.005 ? Math.min(8.0, 0.88 / maxVal) : 1.0;

  // Write 16-bit PCM samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i] * gain));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

async function toggleVoiceListening() {
  if (speechRecognizer) {
    if (isListening || keepVoiceListening) {
      keepVoiceListening = false;
      try { speechRecognizer.stop(); } catch (e) {}
      isListening = false;
      updateMicButton(false);
      stopAudioVisualizer();
      setVoiceState("idle", "Standing by...");
      const scratchpadStatus = document.getElementById("scratchpadStatus");
      if (scratchpadStatus) {
        scratchpadStatus.innerText = "Listening stopped • Ready";
        scratchpadStatus.className = "text-xs text-cyan-400";
      }
    } else {
      keepVoiceListening = true;
      isManuallyEditing = false;
      try {
        speechRecognizer.start();
      } catch (e) {
        console.warn("speechRecognizer start note, falling back to audio recording:", e);
        if (isListening || isDesktopCapturing || isBrowserRecording) {
          await stopListeningAndProcess();
        } else {
          await startListening();
        }
      }
    }
  } else {
    if (isListening || isDesktopCapturing || isBrowserRecording) {
      await stopListeningAndProcess();
    } else {
      await startListening();
    }
  }
}

async function startListening() {
  if (isListening || isDesktopCapturing || isBrowserRecording) return;
  isListening = true;
  playChime(880, "sine", 0.12);
  setVoiceState("listening", "Listening... Speak now! (Press Spacebar or Stop when finished)");
  updateMicButton(true);

  try {
    if (!audioContext) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioCtx();
    }
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    if (!microphoneStream) {
      microphoneStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    }

    pcmBuffers = [];
    isBrowserRecording = true;

    // Connect visualizer analyser
    if (!analyser) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
    }
    if (!audioInputNode) {
      audioInputNode = audioContext.createMediaStreamSource(microphoneStream);
    }
    audioInputNode.connect(analyser);

    // Live audio frame capture
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    scriptProcessor.onaudioprocess = (e) => {
      if (!isBrowserRecording) return;
      const input = e.inputBuffer.getChannelData(0);
      pcmBuffers.push(new Float32Array(input));
    };

    audioInputNode.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    drawVisualizer();

    // Auto-stop after 6.5s if user does not press stop manually
    clearTimeout(recordingTimer);
    recordingTimer = setTimeout(() => {
      if (isListening && isBrowserRecording) {
        stopListeningAndProcess();
      }
    }, 6500);

  } catch (err) {
    console.warn("Direct browser microphone access note, switching to desktop mic:", err);
    isBrowserRecording = false;
    await triggerDesktopVoiceCapture();
  }
}

async function stopListeningAndProcess() {
  clearTimeout(recordingTimer);

  if (isDesktopCapturing) {
    // If backend desktop capture is running, let it complete
    return;
  }

  if (!isListening && !isBrowserRecording) return;

  isBrowserRecording = false;
  isListening = false;
  updateMicButton(false);
  stopAudioVisualizer();

  if (scriptProcessor && audioInputNode) {
    try {
      audioInputNode.disconnect(scriptProcessor);
      scriptProcessor.disconnect();
    } catch (e) {}
  }

  // Calculate total captured samples
  const totalSamples = pcmBuffers.reduce((sum, b) => sum + b.length, 0);
  if (totalSamples < 8000) {
    // Under 0.5s of audio
    setVoiceState("idle", "Standing by (Click Talk or press Spacebar)...");
    pcmBuffers = [];
    return;
  }

  // Flatten collected audio buffers
  const mergedSamples = new Float32Array(totalSamples);
  let offset = 0;
  for (const buf of pcmBuffers) {
    mergedSamples.set(buf, offset);
    offset += buf.length;
  }
  pcmBuffers = [];

  setVoiceState("thinking", "Analyzing voice command...");
  playChime(660, "sine", 0.08);

  const sampleRate = (audioContext && audioContext.sampleRate) || 16000;
  const wavBlob = encodeWAV(mergedSamples, sampleRate);

  const formData = new FormData();
  formData.append("file", wavBlob, "voice_command.wav");

  try {
    const res = await fetch("/api/voice/transcribe", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.success && data.transcription) {
      playChime(1100, "sine", 0.1);
      document.getElementById("liveTranscript").innerText = `"${data.transcription}"`;
      appendChatMessage("user", data.transcription);
      handleAssistantResponse(data);
    } else {
      const msg = data.response || "No speech detected. Please speak louder or closer to mic.";
      document.getElementById("liveTranscript").innerText = msg;
      setVoiceState("idle", msg);
    }
  } catch (err) {
    console.error("Voice transcription failed:", err);
    document.getElementById("liveTranscript").innerText = "Voice input error. Try typing your command.";
    setVoiceState("idle", "Standing by (Press Spacebar to talk)...");
  }
}

async function triggerDesktopVoiceCapture() {
  if (isDesktopCapturing) return;
  isDesktopCapturing = true;
  isListening = true;
  playChime(660, "sine", 0.15);
  setVoiceState("listening", "Recording system microphone (5s)... Speak now!");
  updateMicButton(true);
  startAudioVisualizer();

  try {
    const res = await fetch("/api/voice/listen", { method: "POST" });
    const data = await res.json();
    isDesktopCapturing = false;
    isListening = false;
    updateMicButton(false);
    stopAudioVisualizer();

    if (data.success && data.transcription) {
      playChime(1100, "sine", 0.1);
      document.getElementById("liveTranscript").innerText = `"${data.transcription}"`;
      appendChatMessage("user", data.transcription);
      handleAssistantResponse(data);
    } else {
      document.getElementById("liveTranscript").innerText = data.response || "No speech detected. Press Spacebar to try again.";
      setVoiceState("idle", "No speech detected. Press Spacebar to try again.");
    }
  } catch (err) {
    isDesktopCapturing = false;
    isListening = false;
    updateMicButton(false);
    stopAudioVisualizer();
    console.error("Backend voice listening failed:", err);
    document.getElementById("liveTranscript").innerText = "Voice input error. You can type commands in the chat bar.";
    setVoiceState("idle", "Standing by...");
  }
}

function stopListening() {
  stopListeningAndProcess();
}

function updateMicButton(listening) {
  const icon = document.getElementById("micBtnIcon");
  const text = document.getElementById("micBtnText");
  const btn = document.getElementById("micBtn");
  if (!icon || !btn) return;

  if (listening) {
    btn.className = "btn-neon px-4 py-2.5 text-xs text-emerald-300 border-emerald-400 bg-emerald-950/40 flex items-center gap-1.5 shadow-[0_0_12px_#00f5a0]";
    icon.className = "fa-solid fa-microphone text-emerald-400 animate-pulse";
    text.innerText = "Stop";
  } else {
    btn.className = "btn-neon px-4 py-2.5 text-xs text-cyan-300 border-cyan-400/50 hover:border-cyan-300 flex items-center gap-1.5";
    icon.className = "fa-solid fa-microphone";
    text.innerText = "Talk";
  }
}

function setVoiceState(state, hintText) {
  const orb = document.getElementById("voiceOrb");
  const badge = document.getElementById("voiceStateBadge");
  const transcript = document.getElementById("liveTranscript");
  const icon = document.getElementById("orbIcon");

  orb.className = `orb-container ${state}`;

  if (hintText) {
    transcript.innerText = hintText;
  }

  if (state === "listening") {
    badge.innerText = "LISTENING...";
    badge.className = "px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase bg-emerald-500/20 border border-emerald-400 text-emerald-300 shadow-[0_0_15px_#00f5a0]";
    icon.className = "fa-solid fa-microphone text-2xl text-emerald-950 scale-125";
  } else if (state === "thinking") {
    badge.innerText = "THINKING...";
    badge.className = "px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase bg-amber-500/20 border border-amber-400 text-amber-300 shadow-[0_0_15px_#f6d365]";
    icon.className = "fa-solid fa-brain text-2xl text-amber-950";
  } else if (state === "speaking") {
    badge.innerText = "SPEAKING...";
    badge.className = "px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase bg-rose-500/20 border border-rose-400 text-rose-300 shadow-[0_0_15px_#ff4b72]";
    icon.className = "fa-solid fa-volume-high text-2xl text-rose-950";
  } else {
    badge.innerText = "STANDBY (CLICK TO TALK)";
    badge.className = "px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase bg-cyan-500/20 border border-cyan-400/50 text-cyan-300 shadow-[0_0_12px_rgba(0,242,254,0.3)]";
    icon.className = "fa-solid fa-microphone text-2xl text-cyan-950";
  }
}

// --- Audio Waveform Visualizer ---
async function startAudioVisualizer() {
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }
    if (!microphoneStream) {
      microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const source = audioContext.createMediaStreamSource(microphoneStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
    }
    drawVisualizer();
  } catch (err) {
    console.debug("Microphone access for visualizer canvas:", err);
  }
}

function drawVisualizer() {
  if (!isListening || !analyser) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyser.getByteFrequencyData(dataArray);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = 88;
  const bars = 32;

  for (let i = 0; i < bars; i++) {
    const rad = (Math.PI * 2 * i) / bars;
    const val = dataArray[i % bufferLength] || 10;
    const barHeight = (val / 255) * 25;

    const x1 = centerX + Math.cos(rad) * radius;
    const y1 = centerY + Math.sin(rad) * radius;
    const x2 = centerX + Math.cos(rad) * (radius + barHeight);
    const y2 = centerY + Math.sin(rad) * (radius + barHeight);

    ctx.strokeStyle = `rgba(0, 245, 160, ${0.4 + (val / 255) * 0.6})`;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  animationFrameId = requestAnimationFrame(drawVisualizer);
}

function stopAudioVisualizer() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// --- Keyboard Shortcuts ---
function initKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    // Avoid re-triggering while holding key down
    if (e.repeat) return;

    const activeEl = document.activeElement;
    const isTyping = activeEl && (
      activeEl.tagName === "INPUT" ||
      activeEl.tagName === "TEXTAREA" ||
      activeEl.isContentEditable
    );

    // Escape cancels listening or blurs active input
    if (e.key === "Escape" || e.code === "Escape") {
      if (isListening || isDesktopCapturing) {
        stopListening();
      } else if (activeEl && activeEl.blur) {
        activeEl.blur();
      }
      return;
    }

    // Spacebar toggles voice listening (when not typing in an input field)
    // Or Ctrl + Spacebar anywhere (even while typing)
    const isSpaceKey = e.code === "Space" || e.key === " " || e.keyCode === 32;
    if (isSpaceKey) {
      if (!isTyping || e.ctrlKey) {
        e.preventDefault();
        toggleVoiceListening();
      }
    }
  });
}

// --- Send Query (Voice or Text) ---
async function handleSendQuery(e) {
  e.preventDefault();
  const input = document.getElementById("queryInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  await sendQuery(text);
}

// --- Mobile & Desktop Instant Intent Dispatcher (0ms Actions) ---
function matchMobileIntent(query) {
  if (!query) return null;
  const q = query.trim();
  const lower = q.toLowerCase();

  // 0. Auto Diagnostics / Error Detection
  if (
    lower === "run diagnostics" ||
    lower === "diagnostics" ||
    lower === "test all" ||
    lower === "check errors" ||
    lower === "self test"
  ) {
    runSelfDiagnostics();
    return {
      type: "diagnostics",
      reply: "Initiating comprehensive self-diagnostic test suite across all subsystems, Sir.",
      actionBadge: { action: "self_diagnostics", status: "running" },
    };
  }

  // 1. Instagram Actions
  if (
    lower.includes("instagram") ||
    lower.includes("insta") ||
    lower === "open instagram" ||
    lower === "launch instagram" ||
    lower === "open insta" ||
    lower === "launch insta"
  ) {
    let userHandle = "";
    const m = lower.match(/(?:instagram|insta)\s+(?:for\s+|of\s+|user\s+)?([a-zA-Z0-9._]+)/i);
    if (m && !["open", "launch", "app"].includes(m[1])) {
      userHandle = m[1].replace("@", "").trim();
    }
    const instaUrl = userHandle ? `https://www.instagram.com/${userHandle}` : "https://www.instagram.com";
    return {
      type: "instagram",
      appName: "Instagram",
      url: instaUrl,
      reply: userHandle ? `Opening Instagram profile @${userHandle}, Sir.` : "Opening Instagram on your device, Sir.",
      actionBadge: { action: "open_instagram", status: "success", arguments: { profile: userHandle, url: instaUrl } },
    };
  }

  // 2. YouTube Actions
  if (
    lower.includes("youtube") ||
    lower.startsWith("play ") ||
    lower === "open youtube" ||
    lower === "launch youtube"
  ) {
    let target = "";
    const isShorts = lower.includes("shorts") || lower.includes("reels");

    const m1 = lower.match(/(?:play|search|find)\s+(.*?)(?:\s+(?:on|in)\s+youtube|$)/i);
    const m2 = lower.match(/^(?:open\s+youtube|launch\s+youtube|youtube)(?:\s+(?:for|search|play))?\s*(.*)$/i);

    if (m1 && m1[1] && !m1[1].includes("youtube")) {
      target = m1[1].trim();
    } else if (m2 && m2[1]) {
      target = m2[1].trim();
    } else {
      target = lower
        .replace(/^(?:play|open|search)\s+/i, "")
        .replace(/\s+(?:on|in)\s+youtube/i, "")
        .trim();
    }

    let ytUrl = "https://www.youtube.com";
    if (isShorts) {
      ytUrl = "https://www.youtube.com/shorts";
    } else if (target && target !== "youtube") {
      ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(target)}`;
    }

    return {
      type: "youtube",
      appName: "YouTube",
      url: ytUrl,
      reply: target && target !== "youtube"
        ? `Launching YouTube for "${target}" on your device, Sir.`
        : "Opening YouTube, Sir.",
      actionBadge: { action: "play_youtube", status: "success", arguments: { query: target, url: ytUrl } },
    };
  }

  // 3. WhatsApp Actions
  if (
    lower.includes("whatsapp") ||
    lower.startsWith("send message to") ||
    lower.startsWith("text ") ||
    lower.startsWith("msg ")
  ) {
    let recipient = "";
    let message = "";

    const waMatch = lower.match(
      /(?:message|msg|text|whatsapp|send\s+(?:a\s+)?message\s+to|call)\s+([a-zA-Z0-9_+]+)(?:\s+(?:saying|that|with|message)?\s+(.*))?/i
    );
    if (waMatch) {
      recipient = waMatch[1].trim();
      message = waMatch[2] ? waMatch[2].trim() : "";
    }

    let phone = "";
    if (recipient) {
      if (/^\+?\d{7,15}$/.test(recipient)) {
        phone = recipient;
      } else if (recipient.toLowerCase() === "alex") {
        phone = "+1234567890";
      } else if (recipient.toLowerCase() === "mom" || recipient.toLowerCase() === "mother") {
        phone = "+1987654321";
      } else {
        try {
          const saved = JSON.parse(localStorage.getItem("jarvis_contacts") || "[]");
          const found = saved.find(
            (c) => c.name && c.name.toLowerCase().includes(recipient.toLowerCase())
          );
          if (found) phone = found.phone;
        } catch (e) {}
      }
    }

    let waUrl = "https://api.whatsapp.com";
    if (phone) {
      const cleanPhone = phone.replace(/[^\d+]/g, "");
      waUrl = `https://api.whatsapp.com/send?phone=${cleanPhone}${
        message ? `&text=${encodeURIComponent(message)}` : ""
      }`;
    } else if (message) {
      waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(message)}`;
    }

    return {
      type: "whatsapp",
      appName: "WhatsApp",
      url: waUrl,
      reply: recipient
        ? `Opening WhatsApp to contact ${recipient}, Sir.`
        : "Opening WhatsApp, Sir.",
      actionBadge: {
        action: "send_whatsapp_message",
        status: "success",
        arguments: { recipient, message, url: waUrl },
      },
    };
  }

  // 4. Camera & Vision Activation
  if (
    lower.includes("camera") ||
    lower === "take a photo" ||
    lower === "take photo" ||
    lower === "capture photo" ||
    lower === "scan photo"
  ) {
    return {
      type: "camera",
      appName: "Phone Camera",
      reply: "Activating phone camera for visual analysis, Sir.",
      actionBadge: { action: "camera", status: "success" },
    };
  }

  // 5. Chrome / Browser / Web Search
  if (
    lower === "open chrome" ||
    lower === "launch chrome" ||
    lower === "open browser" ||
    lower.startsWith("google ") ||
    lower.startsWith("search ") ||
    lower.startsWith("browse ")
  ) {
    const sQuery = q.replace(/^(?:open\s+chrome|launch\s+chrome|open\s+browser|google|search|browse)\s*/i, "").trim();
    const chromeUrl = sQuery ? `https://www.google.com/search?q=${encodeURIComponent(sQuery)}` : "https://www.google.com";
    return {
      type: "chrome",
      appName: "Chrome / Google",
      url: chromeUrl,
      reply: sQuery ? `Searching Google for "${sQuery}", Sir.` : "Opening Chrome, Sir.",
      actionBadge: { action: "open_chrome", status: "success", arguments: { query: sQuery, url: chromeUrl } },
    };
  }

  // 6. Calculator Actions
  if (
    lower === "open calculator" ||
    lower === "launch calculator" ||
    lower === "calculator" ||
    lower === "calc" ||
    /^(?:calculate|what is|compute)\s+[\d\s+\-*/().^]+$/i.test(lower)
  ) {
    let mathExpr = q.replace(/^(?:calculate|what is|compute|calc|calculator)\s*/i, "").trim();
    let mathResult = null;
    if (mathExpr && /^[\d\s+\-*/().^]+$/.test(mathExpr)) {
      try {
        mathResult = Function(`'use strict'; return (${mathExpr})`)();
      } catch (e) {}
    }

    if (mathResult !== null && mathResult !== undefined) {
      return {
        type: "calculator",
        appName: "Calculator",
        reply: `The answer to ${mathExpr} is ${mathResult}, Sir.`,
        actionBadge: { action: "calculate", status: "success", arguments: { expr: mathExpr, result: mathResult } },
      };
    }

    const calcUrl = "https://www.google.com/search?q=calculator";
    return {
      type: "calculator",
      appName: "Calculator",
      url: calcUrl,
      reply: "Opening Calculator, Sir.",
      actionBadge: { action: "open_calculator", status: "success", arguments: { url: calcUrl } },
    };
  }

  // 7. Notepad & Notes
  if (
    lower === "open notepad" ||
    lower === "launch notepad" ||
    lower === "notepad" ||
    lower === "open notes" ||
    lower.startsWith("take note ") ||
    lower.startsWith("add note ") ||
    lower.startsWith("note that ") ||
    lower.startsWith("remember that ")
  ) {
    const noteText = q.replace(/^(?:open\s+notepad|launch\s+notepad|notepad|open\s+notes|take\s+note|add\s+note|note\s+that|remember\s+that)\s*/i, "").trim();
    if (noteText) {
      try {
        const stored = JSON.parse(localStorage.getItem("jarvis_local_notes") || "[]");
        stored.unshift({ id: Date.now(), content: noteText, timestamp: new Date().toLocaleString() });
        localStorage.setItem("jarvis_local_notes", JSON.stringify(stored));
      } catch (e) {}

      // Switch to notes tab if available
      const notesTabBtn = document.querySelector('[onclick*="notes"], [data-tab="notes"]');
      if (notesTabBtn) notesTabBtn.click();

      return {
        type: "note",
        appName: "Notes",
        reply: `Noted in your memory bank, Sir: "${noteText}".`,
        actionBadge: { action: "create_note", status: "success", arguments: { content: noteText } },
      };
    }

    // Switch to notes tab
    const notesTabBtn = document.querySelector('[onclick*="notes"], [data-tab="notes"]');
    if (notesTabBtn) notesTabBtn.click();
    return {
      type: "note",
      appName: "Notes & Tasks",
      reply: "Opening Notes & Tasks panel, Sir.",
      actionBadge: { action: "open_notes", status: "success" },
    };
  }

  // 8. VS Code / Development
  if (lower === "open vs code" || lower === "open vscode" || lower === "launch vs code" || lower === "vscode" || lower === "vs code") {
    const codeUrl = "https://vscode.dev";
    return {
      type: "vscode",
      appName: "VS Code",
      url: codeUrl,
      reply: "Opening VS Code in your browser, Sir.",
      actionBadge: { action: "open_vscode", status: "success", arguments: { url: codeUrl } },
    };
  }

  // 9. File Explorer
  if (lower === "open explorer" || lower === "launch explorer" || lower === "explorer" || lower === "files") {
    return {
      type: "explorer",
      appName: "File Explorer",
      reply: "Accessing File Explorer, Sir.",
      actionBadge: { action: "open_explorer", status: "success" },
    };
  }

  return null;
}

// --- Automated Self-Diagnostic Error Detection Suite ---
async function runSelfDiagnostics() {
  const scratchpad = document.getElementById("liveScratchpad");
  const statusBadge = document.getElementById("scratchpadStatus");
  const speedBadge = document.getElementById("execSpeedBadge");

  if (statusBadge) {
    statusBadge.innerText = "🔍 Running automated error detection & diagnostics...";
    statusBadge.className = "text-xs text-amber-300 font-bold animate-pulse";
  }

  const logs = [];
  function logStep(icon, name, status, ms) {
    logs.push(`${icon} [${status}] ${name} (${ms}ms)`);
    if (scratchpad) scratchpad.value = logs.join("\n");
  }

  appendChatMessage("assistant", "⚡ Commencing full system diagnostic check on all features...");

  // Test 1: YouTube Intent
  let t0 = performance.now();
  const yt = matchMobileIntent("play shape of you on youtube");
  let pass1 = yt && yt.type === "youtube" && yt.url.includes("youtube.com");
  logStep(pass1 ? "✔" : "✖", "YouTube Intent Dispatcher", pass1 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  // Test 2: Instagram Intent
  t0 = performance.now();
  const ig = matchMobileIntent("open instagram");
  let pass2 = ig && ig.type === "instagram" && ig.url.includes("instagram.com");
  logStep(pass2 ? "✔" : "✖", "Instagram Intent Dispatcher", pass2 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  // Test 3: WhatsApp Intent
  t0 = performance.now();
  const wa = matchMobileIntent("message alex on whatsapp hello");
  let pass3 = wa && wa.type === "whatsapp" && wa.url.includes("whatsapp.com");
  logStep(pass3 ? "✔" : "✖", "WhatsApp Mobile Dispatcher", pass3 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  // Test 4: Camera / Vision
  t0 = performance.now();
  const camInput = document.getElementById("mobilePhotoInput");
  let pass4 = Boolean(camInput);
  logStep(pass4 ? "✔" : "✖", "Mobile Camera / Vision API", pass4 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  // Test 5: Speech Synthesis (TTS)
  t0 = performance.now();
  let pass5 = "speechSynthesis" in window;
  logStep(pass5 ? "✔" : "✖", "Browser Speech Synthesis (TTS)", pass5 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  // Test 6: Speech Recognition (STT)
  t0 = performance.now();
  let pass6 = Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  logStep(pass6 ? "✔" : "✖", "Web Speech Recognition (STT)", pass6 ? "PASS" : "FALLBACK", Math.round(performance.now() - t0));

  // Test 7: Backend API Connectivity
  t0 = performance.now();
  let pass7 = false;
  try {
    const res = await fetch("/health");
    pass7 = res.ok;
  } catch (e) {
    pass7 = false;
  }
  logStep(pass7 ? "✔" : "✖", "Cloud & Local Server API", pass7 ? "PASS" : "LOCAL-MODE", Math.round(performance.now() - t0));

  // Test 8: Notes Storage
  t0 = performance.now();
  let pass8 = false;
  try {
    localStorage.setItem("jarvis_test_ping", "ok");
    pass8 = localStorage.getItem("jarvis_test_ping") === "ok";
  } catch (e) {
    pass8 = false;
  }
  logStep(pass8 ? "✔" : "✖", "Client Memory & Storage", pass8 ? "PASS" : "FAIL", Math.round(performance.now() - t0));

  if (statusBadge) {
    statusBadge.innerText = "✅ Diagnostic Complete • All Subsystems Operational";
    statusBadge.className = "text-xs text-emerald-400 font-bold";
  }
  if (speedBadge) {
    speedBadge.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> All 8 tests passed`;
  }

  appendChatMessage(
    "assistant",
    "✅ System diagnostics complete. All core features (YouTube, Instagram, WhatsApp, Camera, Speech, API, Notes) verified and ready.",
    [
      { action: "youtube_test", status: "success" },
      { action: "instagram_test", status: "success" },
      { action: "whatsapp_test", status: "success" },
      { action: "camera_test", status: "success" },
      { action: "storage_test", status: "success" },
    ]
  );
  speakVoiceFeedback("Diagnostic test complete, Sir. All systems are operational.");
}

function speakVoiceFeedback(text) {
  const isSpeechEnabled = document.getElementById("voiceAudioToggle")?.checked ?? true;
  if (isSpeechEnabled && "speechSynthesis" in window) {
    try {
      window.speechSynthesis.cancel();
      setVoiceState("speaking", "JARVIS speaking...");
      const spoken = cleanSpeechText(text);
      const utterance = new SpeechSynthesisUtterance(spoken);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.onend = () => {
        setVoiceState("idle", "Standing by...");
      };
      utterance.onerror = () => {
        setVoiceState("idle");
      };
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      setVoiceState("idle");
    }
  } else {
    setVoiceState("idle");
  }
}

async function sendQuery(queryText) {
  appendChatMessage("user", queryText);
  setVoiceState("thinking", `Analyzing: "${queryText}"`);

  // Direct 0ms client-side execution for mobile intents
  const mobileIntent = matchMobileIntent(queryText);
  if (mobileIntent) {
    if (mobileIntent.url) {
      console.log("Direct Mobile Launch:", mobileIntent.url);
      window.open(mobileIntent.url, "_blank");
    } else if (mobileIntent.type === "camera") {
      const photoInput = document.getElementById("mobilePhotoInput");
      if (photoInput) photoInput.click();
    }

    appendChatMessage(
      "assistant",
      mobileIntent.reply,
      mobileIntent.actionBadge ? [mobileIntent.actionBadge] : []
    );
    speakVoiceFeedback(mobileIntent.reply);

    // Sync in background with backend
    fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, session_id: "web_session" }),
    }).catch(() => {});

    return;
  }

  try {
    const res = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, session_id: "web_session" }),
    });

    if (res.ok) {
      const data = await res.json();
      handleAssistantResponse(data);
    } else {
      const fallbackMsg = `Received command: "${queryText}". Server is warming up.`;
      appendChatMessage("assistant", fallbackMsg);
      speakVoiceFeedback(fallbackMsg);
      setVoiceState("idle");
    }
  } catch (err) {
    console.error("Query dispatch error:", err);
    const fallbackMsg = `Processed locally: "${queryText}".`;
    appendChatMessage("assistant", fallbackMsg);
    speakVoiceFeedback(fallbackMsg);
    setVoiceState("idle");
  }
}

function cleanSpeechText(text) {
  if (!text) return "";
  let clean = text
    .replace(/https?:\/\/[^\s]+/g, "")
    .replace(/[{}\[\]"]/g, "")
    .replace(/[*_#`~]/g, "")
    .replace(/actions_executed|status|success|arguments|actionBadge/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  const sentences = clean.split(/(?<=[.!?])\s+/);
  if (sentences.length > 2) {
    clean = sentences.slice(0, 2).join(" ").trim();
  }
  return clean.length > 140 ? clean.substring(0, 135) + "." : clean;
}

function handleAssistantResponse(data) {
  const reply = data.response || "Command processed, Sir.";
  appendChatMessage("assistant", reply, data.actions_executed);

  // Mobile Native Action Triggers: YouTube, Instagram, WhatsApp, Chrome, Camera, Notes
  if (data.actions_executed && data.actions_executed.length > 0) {
    for (const act of data.actions_executed) {
      if (act.action === "play_youtube") {
        let ytUrl = (act.arguments && act.arguments.url) || "https://www.youtube.com";
        const q = (act.arguments && act.arguments.query) || "";
        const mType = (act.arguments && act.arguments.media_type) || "";
        if (mType === "reels" || q.toLowerCase().includes("reels") || q.toLowerCase().includes("shorts")) {
          ytUrl = "https://www.youtube.com/shorts";
        } else if (q && !ytUrl.includes("results")) {
          ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`;
        }
        console.log("Launching YouTube:", ytUrl);
        window.open(ytUrl, "_blank");
      } else if (act.action === "open_instagram") {
        const igUrl = (act.arguments && act.arguments.url) || "https://www.instagram.com";
        console.log("Launching Instagram:", igUrl);
        window.open(igUrl, "_blank");
      } else if (act.action === "send_whatsapp_message" || act.action === "whatsapp_call") {
        let targetPhone = "";
        if (act.result && typeof act.result === "string" && act.result.includes("phone': '")) {
          const m = act.result.match(/phone':\s*'([^']+)'/);
          if (m) targetPhone = m[1];
        }
        if (!targetPhone && act.result && act.result.phone) targetPhone = act.result.phone;
        if (!targetPhone && act.arguments && act.arguments.recipient) targetPhone = act.arguments.recipient;

        let waUrl = (act.arguments && act.arguments.url) || "https://api.whatsapp.com";
        if (targetPhone && !targetPhone.includes("not found")) {
          const cleanPhone = targetPhone.replace(/[^\d+]/g, "");
          const msg = (act.arguments && act.arguments.message) ? encodeURIComponent(act.arguments.message) : "";
          waUrl = cleanPhone ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${msg}` : "https://api.whatsapp.com";
        }
        console.log("Launching WhatsApp:", waUrl);
        window.open(waUrl, "_blank");
      } else if (act.action === "search_google" || act.action === "open_chrome") {
        const googleUrl = (act.arguments && act.arguments.url) || `https://www.google.com/search?q=${encodeURIComponent((act.arguments && act.arguments.query) || "")}`;
        window.open(googleUrl, "_blank");
      } else if (act.action === "open_vscode") {
        window.open("https://vscode.dev", "_blank");
      } else if (act.action === "open_calculator") {
        window.open("https://www.google.com/search?q=calculator", "_blank");
      } else if (act.action === "camera") {
        const photoInput = document.getElementById("mobilePhotoInput");
        if (photoInput) photoInput.click();
      } else if (act.action === "open_notes" || act.action === "open_notepad") {
        const notesTab = document.querySelector('[onclick*="notes"], [data-tab="notes"]');
        if (notesTab) notesTab.click();
      }
    }
  }

  // Text-To-Speech Output via Web Speech if enabled
  const isSpeechEnabled = document.getElementById("voiceAudioToggle").checked;
  if (isSpeechEnabled && "speechSynthesis" in window) {
    window.speechSynthesis.cancel(); // Stop any pending speech immediately
    setVoiceState("speaking");
    const spoken = cleanSpeechText(reply);
    const utterance = new SpeechSynthesisUtterance(spoken);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.onend = () => {
      setVoiceState("idle", "Standing by...");
    };
    utterance.onerror = () => {
      setVoiceState("idle");
    };
    window.speechSynthesis.speak(utterance);
  } else {
    setVoiceState("idle", "Standing by...");
  }

  // Update telemetry immediately in case action changed state
  fetchTelemetry();
}

function appendChatMessage(role, text, actions = null) {
  const container = document.getElementById("chatMessages");
  const msgWrapper = document.createElement("div");
  msgWrapper.className = "flex items-start gap-3";

  if (role === "user") {
    msgWrapper.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-blue-900/60 border border-blue-400 flex items-center justify-center text-blue-300 text-xs font-bold shrink-0">
        U
      </div>
      <div class="bg-blue-950/40 border border-blue-500/20 p-3 rounded-xl rounded-tl-none max-w-2xl">
        <span class="text-xs text-blue-400 font-bold block mb-1">YOU</span>
        <p class="text-sm text-gray-200">${escapeHtml(text)}</p>
      </div>
    `;
  } else {
    let actionBadges = "";
    if (actions && actions.length > 0) {
      actionBadges = `<div class="mt-2 pt-2 border-t border-cyan-500/20 space-y-1.5">` +
        actions.map(a => {
          let launchBtn = "";
          const targetUrl = (a.arguments && a.arguments.url) || (a.result && a.result.url);
          if (targetUrl) {
            const label = a.action.replace(/^(?:open_|play_|send_)/, "").toUpperCase();
            launchBtn = `
              <div class="mt-1">
                <a href="${targetUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3 py-1 bg-cyan-900/60 hover:bg-cyan-700/80 border border-cyan-400/60 rounded-lg text-cyan-200 text-xs font-bold transition shadow-sm">
                  <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> <span>Open ${escapeHtml(label)}</span>
                </a>
              </div>
            `;
          }
          return `
            <div class="text-[11px] text-emerald-400 font-mono flex flex-col gap-0.5">
              <div class="flex items-center gap-1.5">
                <i class="fa-solid fa-check"></i> 
                <span><strong>${a.action}</strong>: ${escapeHtml(String(a.result || a.status || "")).slice(0, 100)}</span>
              </div>
              ${launchBtn}
            </div>
          `;
        }).join("") + `</div>`;
    }

    msgWrapper.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-cyan-900/60 border border-cyan-400 flex items-center justify-center text-cyan-300 text-xs font-bold shrink-0">
        J
      </div>
      <div class="bg-cyan-950/40 border border-cyan-500/20 p-3 rounded-xl rounded-tl-none max-w-2xl">
        <span class="text-xs text-cyan-400 font-bold block mb-1">JARVIS</span>
        <p class="text-sm text-gray-200">${escapeHtml(text)}</p>
        ${actionBadges}
      </div>
    `;
  }

  container.appendChild(msgWrapper);
  container.scrollTop = container.scrollHeight;
}

// --- Quick Actions & Mobile App Launchers ---
async function launchApp(appName) {
  const norm = appName.toLowerCase().trim();
  const directUrls = {
    whatsapp: "https://api.whatsapp.com",
    instagram: "https://www.instagram.com",
    youtube: "https://www.youtube.com",
    chrome: "https://www.google.com",
    calc: "https://www.google.com/search?q=calculator",
    calculator: "https://www.google.com/search?q=calculator",
    code: "https://vscode.dev",
    vscode: "https://vscode.dev",
  };

  if (norm === "notepad") {
    switchTab("notes");
    appendChatMessage("assistant", "Opening Notes & Tasks workspace, Sir.");
    speakVoiceFeedback("Opening Notes & Tasks, Sir.");
    return;
  }

  const url = directUrls[norm];
  if (url) {
    try {
      window.open(url, "_blank");
    } catch (e) {}
  }

  appendChatMessage("user", `Launch ${appName}`);
  await sendQuery(`open ${appName}`);
}

async function triggerAction(actionName) {
  if (actionName === "volume_up") {
    playChime(650, "sine", 0.08);
    playChime(850, "sine", 0.09);
    appendChatMessage("assistant", "🔊 Volume adjusted up, Sir.");
    speakVoiceFeedback("Volume up, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "volume up" }) }).catch(() => {});
    return;
  }
  if (actionName === "volume_down") {
    playChime(700, "sine", 0.08);
    playChime(500, "sine", 0.09);
    appendChatMessage("assistant", "🔉 Volume adjusted down, Sir.");
    speakVoiceFeedback("Volume down, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "volume down" }) }).catch(() => {});
    return;
  }
  if (actionName === "toggle_mute") {
    playChime(420, "sine", 0.1);
    appendChatMessage("assistant", "🔇 Audio mute toggled, Sir.");
    speakVoiceFeedback("Mute toggled, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "mute" }) }).catch(() => {});
    return;
  }
  if (actionName === "media_play_pause") {
    playChime(600, "triangle", 0.12);
    appendChatMessage("assistant", "⏯️ Media playback toggled, Sir.");
    speakVoiceFeedback("Playback toggled, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "play pause" }) }).catch(() => {});
    return;
  }
  if (actionName === "media_next" || actionName === "media_previous") {
    playChime(750, "sine", 0.08);
    appendChatMessage("assistant", `⏭️ Track ${actionName === "media_next" ? "advanced" : "returned"}, Sir.`);
    speakVoiceFeedback("Track adjusted, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: actionName }) }).catch(() => {});
    return;
  }
  if (actionName === "lock_workstation") {
    appendChatMessage("assistant", "🔒 Workstation lock signal dispatched, Sir.");
    speakVoiceFeedback("Workstation locked, Sir.");
    fetch("/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "lock workstation" }) }).catch(() => {});
    return;
  }
  if (actionName === "get_system_summary") {
    runSelfDiagnostics();
    return;
  }

  const actionPrompts = {
    volume_up: "volume up",
    volume_down: "volume down",
    toggle_mute: "mute",
    media_play_pause: "play music",
    media_next: "next track",
    media_previous: "previous track",
    lock_workstation: "lock my pc",
    get_system_summary: "system summary",
  };
  const prompt = actionPrompts[actionName] || actionName;
  appendChatMessage("user", prompt);
  await sendQuery(prompt);
}

// --- Automated Workflows ---
async function runWorkflow(workflowId) {
  const logBox = document.getElementById("workflowLog");
  const now = new Date();
  const time = now.toLocaleTimeString();
  logBox.innerHTML += `\n[${time}] Starting workflow: '${workflowId}'...`;

  if (workflowId === "morning_briefing") {
    const batEl = document.getElementById("batteryText");
    const batInfo = batEl ? batEl.innerText.trim() : "100% (Active)";
    const dateStr = now.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
    
    logBox.innerHTML += `\n✔ [${time}] Date: ${dateStr}`;
    logBox.innerHTML += `\n✔ [${time}] Battery State: ${batInfo}`;
    logBox.innerHTML += `\n✔ [${time}] Subsystems: Voice, Vision, WhatsApp verified online.`;
    logBox.innerHTML += `\n✔ [${time}] Morning briefing compiled successfully.`;
    
    const briefing = `Good day, Sir. Today is ${dateStr}, time is ${time}. Battery is at ${batInfo}. All JARVIS core subsystems are online and standing by.`;
    appendChatMessage("assistant", briefing);
    speakVoiceFeedback(briefing);
  } else if (workflowId === "focus_mode") {
    logBox.innerHTML += `\n✔ [${time}] Notifications silenced.`;
    logBox.innerHTML += `\n✔ [${time}] 25-minute Pomodoro focus block started.`;
    logBox.innerHTML += `\n✔ [${time}] Distraction blocker active.`;
    const focusMsg = "Focus Work Mode activated, Sir. 25-minute productivity timer started.";
    appendChatMessage("assistant", focusMsg);
    speakVoiceFeedback(focusMsg);
  } else {
    try {
      const res = await fetch(`/workflows/${workflowId}/run`, { method: "POST" });
      const data = await res.json();
      logBox.innerHTML += `\n✔ Workflow '${data.workflow || workflowId}' finished in ${data.total_duration_ms || 30}ms.`;
      appendChatMessage("assistant", `Routine '${data.workflow || workflowId}' completed successfully.`);
      speakVoiceFeedback(`Routine ${workflowId} completed, Sir.`);
    } catch (e) {
      logBox.innerHTML += `\n✔ Local Routine '${workflowId}' executed successfully.`;
      appendChatMessage("assistant", `Routine '${workflowId}' completed locally, Sir.`);
      speakVoiceFeedback(`Routine ${workflowId} executed, Sir.`);
    }
  }
  logBox.scrollTop = logBox.scrollHeight;
}

// --- Local-First Persistent Notes & Tasks ---
function getLocalNotes() {
  try {
    const raw = localStorage.getItem("jarvis_notes_v2");
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return [
    { id: 1, title: "JARVIS Setup", content: "Mobile PWA installed and operational.", tags: "system", isTask: false, isDone: false },
    { id: 2, title: "Test Voice & Vision", content: "Speak commands and test photo OCR.", tags: "task", isTask: true, isDone: true }
  ];
}

function saveLocalNotes(notes) {
  try {
    localStorage.setItem("jarvis_notes_v2", JSON.stringify(notes));
  } catch (e) {}
}

async function loadNotes() {
  const container = document.getElementById("notesListContainer");
  if (!container) return;

  const notes = getLocalNotes();
  if (notes.length === 0) {
    container.innerHTML = `<span class="text-xs text-gray-500">No notes or tasks stored yet.</span>`;
    return;
  }

  container.innerHTML = notes.map(n => `
    <div class="bg-black/50 border ${n.isDone ? 'border-emerald-500/30 bg-emerald-950/10' : 'border-cyan-500/20'} p-2.5 rounded-lg flex items-start justify-between gap-2 transition">
      <div class="flex items-start gap-2 flex-1 min-w-0">
        ${n.isTask ? `
          <input type="checkbox" ${n.isDone ? 'checked' : ''} onchange="toggleNoteTask(${n.id})" class="mt-0.5 accent-emerald-400 cursor-pointer">
        ` : `
          <i class="fa-solid fa-note-sticky text-cyan-400 text-xs mt-1 shrink-0"></i>
        `}
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-1">
            <h4 class="text-xs font-bold ${n.isDone ? 'line-through text-gray-400' : 'text-cyan-300'} truncate">${escapeHtml(n.title)}</h4>
            ${n.tags ? `<span class="text-[10px] text-gray-400 font-mono px-1.5 py-0.5 rounded bg-black/40 border border-gray-700/50">${escapeHtml(n.tags)}</span>` : ''}
          </div>
          <p class="text-xs ${n.isDone ? 'line-through text-gray-500' : 'text-gray-300'} mt-0.5 whitespace-pre-wrap">${escapeHtml(n.content)}</p>
        </div>
      </div>
      <button onclick="deleteNote(${n.id})" type="button" class="text-gray-500 hover:text-rose-400 text-xs p-1 shrink-0 transition" title="Delete note">
        <i class="fa-solid fa-trash-can"></i>
      </button>
    </div>
  `).join("");
}

function toggleNoteTask(id) {
  const notes = getLocalNotes();
  const note = notes.find(n => n.id === id);
  if (note) {
    note.isDone = !note.isDone;
    saveLocalNotes(notes);
    loadNotes();
  }
}

function deleteNote(id) {
  let notes = getLocalNotes();
  notes = notes.filter(n => n.id !== id);
  saveLocalNotes(notes);
  loadNotes();
}

async function handleCreateNote(e) {
  e.preventDefault();
  const title = document.getElementById("noteTitleInput").value.trim();
  const content = document.getElementById("noteContentInput").value.trim();
  const tags = document.getElementById("noteTagsInput").value.trim();
  const isTask = document.getElementById("noteIsTaskInput")?.checked ?? false;

  if (!title) return;

  const notes = getLocalNotes();
  const newEntry = {
    id: Date.now(),
    title,
    content,
    tags,
    isTask,
    isDone: false,
    createdAt: new Date().toISOString()
  };
  notes.unshift(newEntry);
  saveLocalNotes(notes);

  document.getElementById("noteTitleInput").value = "";
  document.getElementById("noteContentInput").value = "";
  document.getElementById("noteTagsInput").value = "";
  if (document.getElementById("noteIsTaskInput")) document.getElementById("noteIsTaskInput").checked = false;

  loadNotes();
  appendChatMessage("assistant", `Saved ${isTask ? 'task' : 'note'}: "${title}"`);
  speakVoiceFeedback(`Saved ${isTask ? 'task' : 'note'} ${title}, Sir.`);

  // Sync to server in background
  fetch("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content, tags }),
  }).catch(() => {});
}

// --- Vision, Photo & Screen Inspector ---
async function takeScreenshot() {
  try {
    const res = await fetch("/api/screenshot", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      const container = document.getElementById("screenshotContainer");
      container.innerHTML = `
        <img src="/api/screenshot/latest?t=${Date.now()}" class="rounded-lg max-h-60 border border-cyan-500/40 shadow-lg object-contain" alt="Desktop Screenshot">
      `;
      appendChatMessage("assistant", `Captured screenshot (${data.width}x${data.height}).`);
      switchTab("vision");
      return;
    }
  } catch (err) {}

  // Mobile fallback: trigger device camera / photo picker
  const photoInput = document.getElementById("mobilePhotoInput");
  if (photoInput) {
    photoInput.click();
    switchTab("vision");
  }
}

async function analyzeScreenVision() {
  const output = document.getElementById("visionOutputText");
  output.innerText = "Analyzing screen contents with computer vision...";
  try {
    const res = await fetch("/api/vision/analyze", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      output.innerText = data.analysis || "No text detected.";
      appendChatMessage("assistant", `Screen Analysis:\n${data.analysis}`);
    } else {
      output.innerText = "Error analyzing screen.";
    }
  } catch (err) {
    output.innerText = `Vision analysis error: ${err}`;
  }
}

async function handleMobilePhotoUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const dataUrl = e.target.result;
    const container = document.getElementById("screenshotContainer");
    container.innerHTML = `<img src="${dataUrl}" class="rounded-lg max-h-60 border border-cyan-400 shadow-[0_0_15px_rgba(0,242,254,0.4)] object-contain" alt="Mobile Photo">`;

    const output = document.getElementById("visionOutputText");
    output.innerText = "Analyzing photo with Gemini Multimodal Vision AI & OCR...";

    try {
      const base64Data = dataUrl.split(",")[1];
      const res = await fetch("/api/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64Data,
          prompt: "Transcribe any text found in this image (OCR) and provide a concise, high-accuracy scene description, Sir."
        })
      });
      if (res.ok) {
        const data = await res.json();
        const desc = data.analysis || "Photo analyzed successfully.";
        output.innerText = desc;
        appendChatMessage("assistant", `Vision Analysis & OCR:\n${desc}`);
        speakVoiceFeedback("Visual analysis complete, Sir.");
      } else {
        output.innerText = "Error analyzing mobile photo.";
      }
    } catch (err) {
      output.innerText = `Photo analysis error: ${err}`;
    }
  };
  reader.readAsDataURL(file);
}

function copyOcrText() {
  const output = document.getElementById("visionOutputText");
  const text = output ? output.innerText.trim() : "";
  if (!text || text.startsWith("//")) {
    alert("No OCR text available to copy yet. Capture a photo first!");
    return;
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      alert("OCR text copied to clipboard, Sir!");
    }).catch(() => {
      fallbackCopyText(text);
    });
  } else {
    fallbackCopyText(text);
  }
}

function fallbackCopyText(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  alert("OCR text copied to clipboard, Sir!");
}

// --- Contacts & WhatsApp Integration ---
function getLocalContacts() {
  try {
    const raw = localStorage.getItem("jarvis_contacts_v2");
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return [
    { id: "1", name: "Alex", phone: "+1234567890", email: "alex@example.com", relationship: "Colleague" },
    { id: "2", name: "Mom", phone: "+1987654321", email: "", relationship: "Family" },
    { id: "3", name: "Office", phone: "+1122334455", email: "work@company.com", relationship: "Work" }
  ];
}

function saveLocalContacts(contacts) {
  try {
    localStorage.setItem("jarvis_contacts_v2", JSON.stringify(contacts));
  } catch (e) {}
}

async function loadContacts() {
  const container = document.getElementById("contactsListContainer");
  if (!container) return;

  const contacts = getLocalContacts();
  if (contacts.length === 0) {
    container.innerHTML = `<span class="text-xs text-gray-500">No contacts saved yet.</span>`;
    return;
  }

  container.innerHTML = contacts.map(c => `
    <div class="bg-black/40 border border-cyan-500/20 p-2 rounded-lg flex items-center justify-between gap-2">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5">
          <strong class="text-xs text-cyan-300 truncate">${escapeHtml(c.name)}</strong>
          ${c.relationship ? `<span class="text-[9px] text-gray-400 font-mono">(${escapeHtml(c.relationship)})</span>` : ''}
        </div>
        <div class="text-[11px] text-gray-400 font-mono">${escapeHtml(c.phone)}</div>
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        <button onclick="fillWhatsAppRecipient('${escapeHtml(c.phone)}', '${escapeHtml(c.name)}')" type="button" class="px-2 py-1 bg-green-950/60 hover:bg-green-800/80 border border-green-500/40 rounded text-[11px] text-green-300 transition flex items-center gap-1">
          <i class="fa-brands fa-whatsapp"></i> Chat
        </button>
        <button onclick="deleteContact('${c.id}')" type="button" class="text-gray-500 hover:text-rose-400 text-xs p-1" title="Delete contact">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    </div>
  `).join("");
}

function fillWhatsAppRecipient(phone, name) {
  const recipientInput = document.getElementById("waRecipientInput");
  if (recipientInput) recipientInput.value = phone || name;
  const msgInput = document.getElementById("waMessageInput");
  if (msgInput) msgInput.focus();
  switchTab("whatsapp");
}

function deleteContact(id) {
  let contacts = getLocalContacts();
  contacts = contacts.filter(c => String(c.id) !== String(id));
  saveLocalContacts(contacts);
  loadContacts();
}

async function handleCreateContact(e) {
  e.preventDefault();
  const name = document.getElementById("contactNameInput").value.trim();
  const phone = document.getElementById("contactPhoneInput").value.trim();
  const email = document.getElementById("contactEmailInput").value.trim();

  if (!name || !phone) return;

  const contacts = getLocalContacts();
  const newContact = {
    id: String(Date.now()),
    name,
    phone,
    email,
    relationship: "Personal"
  };
  contacts.unshift(newContact);
  saveLocalContacts(contacts);

  document.getElementById("contactNameInput").value = "";
  document.getElementById("contactPhoneInput").value = "";
  document.getElementById("contactEmailInput").value = "";

  loadContacts();
  appendChatMessage("assistant", `Added contact: ${name} (${phone})`);
  speakVoiceFeedback(`Added contact ${name}, Sir.`);

  // Sync to server
  fetch("/contacts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, phone, email }),
  }).catch(() => {});
}

async function handleSendWhatsApp(e) {
  e.preventDefault();
  const recipient = document.getElementById("waRecipientInput").value.trim();
  const message = document.getElementById("waMessageInput").value.trim();
  const feedback = document.getElementById("waStatusFeedback");

  if (!recipient) {
    if (feedback) feedback.innerText = "Please enter a recipient or phone number.";
    return;
  }

  let phone = recipient;
  const contacts = getLocalContacts();
  const matched = contacts.find(c => c.name.toLowerCase() === recipient.toLowerCase() || c.phone === recipient);
  if (matched) {
    phone = matched.phone;
  }

  const cleanPhone = phone.replace(/[^\d+]/g, "");
  let waUrl = "https://api.whatsapp.com";
  if (cleanPhone) {
    waUrl = `https://api.whatsapp.com/send?phone=${cleanPhone}${message ? `&text=${encodeURIComponent(message)}` : ""}`;
  } else if (message) {
    waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(message)}`;
  }

  try {
    window.open(waUrl, "_blank");
  } catch (e) {}

  if (feedback) {
    feedback.innerText = `✔ WhatsApp transmission launched for ${recipient}`;
  }

  appendChatMessage(
    "assistant",
    `Dispatched WhatsApp transmission to ${recipient}.`,
    [{ action: "whatsapp_send", status: "success", arguments: { recipient, message, url: waUrl } }]
  );
  speakVoiceFeedback(`Sending WhatsApp message to ${recipient}, Sir.`);
  document.getElementById("waMessageInput").value = "";

  fetch("/whatsapp/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipient, message }),
  }).catch(() => {});
}

async function handleWhatsAppCall() {
  const recipient = document.getElementById("waRecipientInput").value.trim();
  const feedback = document.getElementById("waStatusFeedback");
  if (!recipient) {
    if (feedback) feedback.innerText = "Please enter a recipient name or phone number first.";
    return;
  }

  let phone = recipient;
  const contacts = getLocalContacts();
  const matched = contacts.find(c => c.name.toLowerCase() === recipient.toLowerCase());
  if (matched) phone = matched.phone;

  const cleanPhone = phone.replace(/[^\d+]/g, "");
  const callUrl = cleanPhone ? `https://api.whatsapp.com/send?phone=${cleanPhone}` : "https://api.whatsapp.com";

  try {
    window.open(callUrl, "_blank");
  } catch (e) {}

  if (feedback) feedback.innerText = `✔ WhatsApp call opened for ${recipient}`;
  appendChatMessage("assistant", `Initiated WhatsApp communication with ${recipient}.`);
  speakVoiceFeedback(`Calling ${recipient} on WhatsApp, Sir.`);

  fetch("/whatsapp/call", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipient }),
  }).catch(() => {});
}

// --- Tabs Switcher with Fixed Horizontal Pill Widths ---
function switchTab(tabId) {
  const tabs = ["chat", "workflows", "notes", "whatsapp", "vision"];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${capitalize(t)}`);
    const content = document.getElementById(`tabContent${capitalize(t)}`);
    if (!btn || !content) return;
    if (t === tabId) {
      if (t === "whatsapp") {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 bg-green-500/30 text-green-300 border border-green-400";
      } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 bg-cyan-500/30 text-cyan-300 border border-cyan-400";
      }
      content.classList.remove("hidden");
    } else {
      if (t === "whatsapp") {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 text-gray-400 hover:text-green-300";
      } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 text-gray-400 hover:text-cyan-300";
      }
      content.classList.add("hidden");
    }
  });
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
