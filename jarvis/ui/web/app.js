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
  initWebSocket();
  initWebSpeech();
  initKeyboardShortcuts();
  loadNotes();
  loadContacts();

  // Periodic polling fallback for telemetry if WS is reconnecting
  setInterval(fetchTelemetry, 3000);
});

// --- Live Clock ---
function initLiveClock() {
  const clockEl = document.getElementById("liveClock");
  const dateEl = document.getElementById("liveDate");

  function update() {
    const now = new Date();
    clockEl.innerText = now.toLocaleTimeString();
    dateEl.innerText = now.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  }
  update();
  setInterval(update, 1000);
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
  if (metrics.battery) {
    document.getElementById("batteryText").innerHTML = `<i class="fa-solid fa-battery-half text-cyan-400"></i> ${metrics.battery}`;
  }

  // Uptime
  if (metrics.uptime) {
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

function executeScratchpadCommand() {
  clearTimeout(autoExecuteTimer);
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
    speechRecognizer.continuous = false;
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
        scratchpadStatus.innerText = "🎙️ Listening live in real-time...";
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
        scratchpadStatus.innerText = "✏️ Live text (you can edit to correct)";
        scratchpadStatus.className = "text-xs text-amber-300 font-medium";
      }

      if (event.results[event.results.length - 1].isFinal) {
        // Pause briefly before running to allow manual correction
        clearTimeout(autoExecuteTimer);
        autoExecuteTimer = setTimeout(() => {
          if (!isManuallyEditing && scratchpad && scratchpad.value.trim()) {
            executeScratchpadCommand();
          }
        }, 1200);
      }
    };

    speechRecognizer.onerror = async (event) => {
      console.warn("Speech recognition note:", event.error);
      if (event.error !== "no-speech") {
        if (scratchpadStatus) scratchpadStatus.innerText = `Note: ${event.error}`;
      }
      stopListening();
    };

    speechRecognizer.onend = () => {
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
    if (isListening) {
      try { speechRecognizer.stop(); } catch (e) {}
      isListening = false;
      updateMicButton(false);
      stopAudioVisualizer();
      setVoiceState("idle", "Standing by...");
    } else {
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

async function sendQuery(queryText) {
  appendChatMessage("user", queryText);
  setVoiceState("thinking", `Analyzing: "${queryText}"`);

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
      appendChatMessage("assistant", "Error processing command. Please try again.");
      setVoiceState("idle");
    }
  } catch (err) {
    console.error("Query dispatch error:", err);
    appendChatMessage("assistant", `Connection failure: ${err}`);
    setVoiceState("idle");
  }
}

function cleanSpeechText(text) {
  if (!text) return "";
  let clean = text.replace(/[\*#_`]/g, "").trim();
  const sentences = clean.split(/(?<=[.!?])\s+/);
  if (sentences.length > 2) {
    clean = sentences.slice(0, 2).join(" ").trim();
  }
  return clean.length > 220 ? clean.substring(0, 215) + "." : clean;
}

function handleAssistantResponse(data) {
  const reply = data.response || "Command processed, Sir.";
  appendChatMessage("assistant", reply, data.actions_executed);

  // Mobile Native Action Triggers: YouTube, WhatsApp, and Google Web search
  if (data.actions_executed && data.actions_executed.length > 0) {
    for (const act of data.actions_executed) {
      if (act.action === "play_youtube") {
        let ytUrl = "https://www.youtube.com";
        const q = (act.arguments && act.arguments.query) || "";
        const mType = (act.arguments && act.arguments.media_type) || "";
        if (mType === "reels" || q.toLowerCase().includes("reels") || q.toLowerCase().includes("shorts")) {
          ytUrl = "https://www.youtube.com/shorts";
        } else if (q) {
          ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`;
        }
        console.log("Launching YouTube on mobile:", ytUrl);
        setTimeout(() => { window.open(ytUrl, "_blank"); }, 600);
      } else if (act.action === "send_whatsapp_message" || act.action === "whatsapp_call") {
        let targetPhone = "";
        if (act.result && typeof act.result === "string" && act.result.includes("phone': '")) {
          const m = act.result.match(/phone':\s*'([^']+)'/);
          if (m) targetPhone = m[1];
        }
        if (!targetPhone && act.result && act.result.phone) targetPhone = act.result.phone;
        if (!targetPhone && act.arguments && act.arguments.recipient) targetPhone = act.arguments.recipient;

        if (targetPhone && !targetPhone.includes("not found")) {
          const cleanPhone = targetPhone.replace(/[^\d+]/g, "");
          const msg = (act.arguments && act.arguments.message) ? encodeURIComponent(act.arguments.message) : "";
          const waUrl = cleanPhone ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${msg}` : "https://web.whatsapp.com";
          console.log("Launching WhatsApp on mobile:", waUrl);
          setTimeout(() => { window.open(waUrl, "_blank"); }, 600);
        }
      } else if (act.action === "search_google" && act.arguments && act.arguments.query) {
        const googleUrl = `https://www.google.com/search?q=${encodeURIComponent(act.arguments.query)}`;
        setTimeout(() => { window.open(googleUrl, "_blank"); }, 600);
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
      actionBadges = `<div class="mt-2 pt-2 border-t border-cyan-500/20 space-y-1">` +
        actions.map(a => `
          <div class="text-[11px] text-emerald-400 font-mono flex items-center gap-1.5">
            <i class="fa-solid fa-check"></i> 
            <span><strong>${a.action}</strong>: ${escapeHtml(String(a.result || a.status || "")).slice(0, 100)}</span>
          </div>
        `).join("") + `</div>`;
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

// --- Quick Actions ---
async function launchApp(appName) {
  appendChatMessage("user", `Launch ${appName}`);
  await sendQuery(`open ${appName}`);
}

async function triggerAction(actionName) {
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

// --- Workflows ---
async function runWorkflow(workflowId) {
  const logBox = document.getElementById("workflowLog");
  logBox.innerHTML += `\n[${new Date().toLocaleTimeString()}] Triggering workflow: ${workflowId}...`;
  
  try {
    const res = await fetch(`/workflows/${workflowId}/run`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      logBox.innerHTML += `\n✔ Workflow '${data.workflow}' finished in ${data.total_duration_ms}ms (${data.step_results.length} steps).`;
      appendChatMessage("assistant", `Routine '${data.workflow}' completed successfully.`);
    } else {
      logBox.innerHTML += `\n✖ Workflow error: ${data.detail || "Execution failed"}`;
    }
    logBox.scrollTop = logBox.scrollHeight;
  } catch (err) {
    logBox.innerHTML += `\n✖ Error: ${err}`;
  }
}

// --- Notes Management ---
async function loadNotes() {
  const container = document.getElementById("notesListContainer");
  try {
    const res = await fetch("/notes");
    if (res.ok) {
      const notes = await res.json();
      if (notes.length === 0) {
        container.innerHTML = `<span class="text-xs text-gray-500">No notes stored yet.</span>`;
        return;
      }
      container.innerHTML = notes.map(n => `
        <div class="bg-black/40 border border-cyan-500/20 p-2.5 rounded-lg">
          <div class="flex justify-between items-start">
            <h4 class="text-xs font-bold text-cyan-300">${escapeHtml(n.title)}</h4>
            <span class="text-[10px] text-gray-500 font-mono">${escapeHtml(n.tags || "")}</span>
          </div>
          <p class="text-xs text-gray-300 mt-1">${escapeHtml(n.content)}</p>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Error loading notes:", e);
  }
}

async function handleCreateNote(e) {
  e.preventDefault();
  const title = document.getElementById("noteTitleInput").value;
  const content = document.getElementById("noteContentInput").value;
  const tags = document.getElementById("noteTagsInput").value;

  try {
    const res = await fetch("/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content, tags }),
    });
    if (res.ok) {
      document.getElementById("noteTitleInput").value = "";
      document.getElementById("noteContentInput").value = "";
      document.getElementById("noteTagsInput").value = "";
      loadNotes();
      appendChatMessage("assistant", `Saved note: "${title}"`);
    }
  } catch (err) {
    console.error("Error creating note:", err);
  }
}

// --- Vision & Screen Inspector ---
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
    }
  } catch (err) {
    console.error("Screenshot error:", err);
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
    output.innerText = "Analyzing photo with Gemini Multimodal Vision AI...";

    try {
      const base64Data = dataUrl.split(",")[1];
      const res = await fetch("/api/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64Data, query: "Describe and explain what you see in this photo in detail, Sir." })
      });
      if (res.ok) {
        const data = await res.json();
        const desc = data.analysis || "Photo analyzed successfully.";
        output.innerText = desc;
        appendChatMessage("assistant", `Photo Analysis:\n${desc}`);
        handleAssistantResponse({ response: desc });
      } else {
        output.innerText = "Error analyzing mobile photo.";
      }
    } catch (err) {
      output.innerText = `Photo analysis error: ${err}`;
    }
  };
  reader.readAsDataURL(file);
}

// --- Contacts & WhatsApp Integration ---
async function loadContacts() {
  const container = document.getElementById("contactsListContainer");
  if (!container) return;
  try {
    const res = await fetch("/contacts");
    if (res.ok) {
      const contacts = await res.json();
      if (contacts.length === 0) {
        container.innerHTML = `<span class="text-xs text-gray-500">No contacts saved yet.</span>`;
        return;
      }
      container.innerHTML = contacts.map(c => `
        <div class="bg-black/40 border border-cyan-500/20 p-2.5 rounded-lg flex items-center justify-between">
          <div>
            <h4 class="text-xs font-bold text-cyan-300">${escapeHtml(c.name)}</h4>
            <span class="text-[11px] text-gray-400 font-mono">${escapeHtml(c.phone)}</span>
            ${c.email ? `<span class="text-[10px] text-gray-500 block">${escapeHtml(c.email)}</span>` : ""}
          </div>
          <div class="flex items-center gap-1.5">
            <button onclick="selectContactForWhatsApp('${escapeHtml(c.name)}', '${escapeHtml(c.phone)}')" class="btn-neon px-2 py-1 text-[11px] border-green-500/30 text-green-300" title="Text via WhatsApp">
              <i class="fa-brands fa-whatsapp"></i>
            </button>
            <button onclick="triggerWhatsAppCall('${escapeHtml(c.phone)}')" class="btn-neon px-2 py-1 text-[11px] border-emerald-500/30 text-emerald-300" title="Call via WhatsApp">
              <i class="fa-solid fa-phone"></i>
            </button>
          </div>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Error loading contacts:", e);
  }
}

function selectContactForWhatsApp(name, phone) {
  document.getElementById("waRecipientInput").value = name || phone;
  document.getElementById("waMessageInput").focus();
  switchTab("whatsapp");
}

async function handleCreateContact(e) {
  e.preventDefault();
  const name = document.getElementById("contactNameInput").value;
  const phone = document.getElementById("contactPhoneInput").value;
  const email = document.getElementById("contactEmailInput").value;

  try {
    const res = await fetch("/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, phone, email }),
    });
    if (res.ok) {
      document.getElementById("contactNameInput").value = "";
      document.getElementById("contactPhoneInput").value = "";
      document.getElementById("contactEmailInput").value = "";
      loadContacts();
      appendChatMessage("assistant", `Added contact: ${name} (${phone})`);
    }
  } catch (err) {
    console.error("Error adding contact:", err);
  }
}

async function handleSendWhatsApp(e) {
  e.preventDefault();
  const recipient = document.getElementById("waRecipientInput").value;
  const message = document.getElementById("waMessageInput").value;
  const feedback = document.getElementById("waStatusFeedback");

  feedback.innerText = `Dispatching WhatsApp transmission to ${recipient}...`;
  try {
    const res = await fetch("/whatsapp/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient, message }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      feedback.innerText = `✔ ${data.feedback}`;
      appendChatMessage("assistant", data.feedback);
      document.getElementById("waMessageInput").value = "";
    } else {
      feedback.innerText = `✖ ${data.message || data.error || "Failed to launch WhatsApp."}`;
      appendChatMessage("assistant", `Could not send WhatsApp message: ${data.error || "Invalid recipient"}`);
    }
  } catch (err) {
    feedback.innerText = `✖ Error: ${err}`;
  }
}

async function handleWhatsAppCall() {
  const recipient = document.getElementById("waRecipientInput").value;
  const feedback = document.getElementById("waStatusFeedback");
  if (!recipient) {
    alert("Please enter a recipient name or phone number first.");
    return;
  }
  await triggerWhatsAppCall(recipient);
}

async function triggerWhatsAppCall(recipient) {
  const feedback = document.getElementById("waStatusFeedback");
  if (feedback) feedback.innerText = `Initiating WhatsApp call with ${recipient}...`;

  try {
    const res = await fetch("/whatsapp/call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      if (feedback) feedback.innerText = `✔ ${data.feedback}`;
      appendChatMessage("assistant", data.feedback);
    } else {
      if (feedback) feedback.innerText = `✖ ${data.message || data.error || "Failed to start call."}`;
      appendChatMessage("assistant", `Could not start WhatsApp call: ${data.error || "Invalid recipient"}`);
    }
  } catch (err) {
    if (feedback) feedback.innerText = `✖ Call error: ${err}`;
  }
}

// --- Tabs Switcher ---
function switchTab(tabId) {
  const tabs = ["chat", "workflows", "notes", "whatsapp", "vision"];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${capitalize(t)}`);
    const content = document.getElementById(`tabContent${capitalize(t)}`);
    if (!btn || !content) return;
    if (t === tabId) {
      if (t === "whatsapp") {
        btn.className = "px-4 py-2 rounded-lg text-xs font-bold tracking-wider uppercase transition-all bg-green-500/30 text-green-300 border border-green-400";
      } else {
        btn.className = "px-4 py-2 rounded-lg text-xs font-bold tracking-wider uppercase transition-all bg-cyan-500/30 text-cyan-300 border border-cyan-400";
      }
      content.classList.remove("hidden");
    } else {
      btn.className = "px-4 py-2 rounded-lg text-xs font-bold tracking-wider uppercase transition-all text-gray-400 hover:text-cyan-300 hover:bg-cyan-950/40";
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
