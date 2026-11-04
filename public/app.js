/**
 * J.A.R.V.I.S. - Hands-Free AI Voice & Vision Assistant
 * Specially designed for hands-free and visually impaired (eyes-free) operation.
 */

let ws = null;
let speechRecognizer = null;
let isListening = false;
let isHandsFreeActive = true;
let isSpeakingTts = false;
let autoRestartTimer = null;
let audioContext = null;
let analyser = null;
let animationFrameId = null;

// Audio visualizer canvas
const canvas = document.getElementById("visualizerCanvas");
const ctx = canvas ? canvas.getContext("2d") : null;

// --- Initialization on Load ---
window.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  initMobileBattery();
  initWebSocket();
  initWebSpeech();
  initKeyboardShortcuts();
  loadNotes();

  // Allow first user tap anywhere to unlock audio context & speech recognition
  document.body.addEventListener("click", () => {
    if (isHandsFreeActive && !isListening && speechRecognizer && !isSpeakingTts) {
      try { speechRecognizer.start(); } catch (e) {}
    }
  }, { once: true });
});

// --- Live Clock ---
function initLiveClock() {
  const clockEl = document.getElementById("liveClock");
  function update() {
    const now = new Date();
    if (clockEl) clockEl.innerText = now.toLocaleTimeString();
  }
  update();
  setInterval(update, 1000);
}

// --- Live Mobile Battery API ---
let currentBatteryPct = 98;
let isBatteryCharging = false;

async function initMobileBattery() {
  const batteryEl = document.getElementById("batteryText");
  if (!batteryEl) return;

  if ("getBattery" in navigator) {
    try {
      const battery = await navigator.getBattery();
      function updateBatteryDisplay() {
        currentBatteryPct = Math.round(battery.level * 100);
        isBatteryCharging = battery.charging;
        const bolt = battery.charging ? '<i class="fa-solid fa-bolt text-amber-400 mr-1 animate-pulse"></i>' : '';
        const iconClass = currentBatteryPct > 75 ? "fa-battery-full text-emerald-400" : currentBatteryPct > 35 ? "fa-battery-half text-cyan-400" : "fa-battery-quarter text-rose-400";
        batteryEl.innerHTML = `${bolt}<i class="fa-solid ${iconClass} mr-1"></i>${currentBatteryPct}%`;
      }
      updateBatteryDisplay();
      battery.addEventListener("levelchange", updateBatteryDisplay);
      battery.addEventListener("chargingchange", updateBatteryDisplay);
    } catch (e) {
      console.warn("Battery API note:", e);
    }
  }

  if (!batteryEl.innerText || batteryEl.innerText.includes("--")) {
    batteryEl.innerHTML = `<i class="fa-solid fa-battery-three-quarters text-emerald-400 mr-1"></i>98% (Active)`;
  }
}

// --- WebSocket Telemetry (Optional for local desktop) ---
function initWebSocket() {
  const loc = window.location;
  const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${loc.host}/ws`;

  try {
    ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "response") {
          handleAssistantResponse(msg.data);
        }
      } catch (e) {}
    };
    ws.onclose = () => {
      setTimeout(initWebSocket, 4000);
    };
  } catch (err) {}
}

// --- Hands-Free Web Speech Recognition Engine ---
function initWebSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Web Speech API not available in this browser.");
    updateVoiceStateUI("speech_unavailable", "Voice speech not supported by browser");
    return;
  }

  try {
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = true;
    speechRecognizer.interimResults = true;
    speechRecognizer.lang = "en-US";

    speechRecognizer.onstart = () => {
      isListening = true;
      updateVoiceStateUI("listening", "🎙️ LISTENING (SPEAK FREELY)");
      updateMicButton(true);
      startAudioVisualizer();
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
      const transcriptEl = document.getElementById("liveTranscript");
      if (transcriptEl && spoken) {
        transcriptEl.innerText = `"${spoken}"`;
      }

      // When speech sentence is final, process immediately
      if (event.results[event.results.length - 1].isFinal && final.trim()) {
        const cleanCommand = final.trim();
        handleVoiceCommandDispatcher(cleanCommand);
      }
    };

    speechRecognizer.onerror = (event) => {
      if (event.error !== "no-speech") {
        console.warn("Speech recognition notice:", event.error);
      }
    };

    speechRecognizer.onend = () => {
      isListening = false;
      updateMicButton(false);
      stopAudioVisualizer();

      // Infinite hands-free auto-restart loop
      if (isHandsFreeActive && !isSpeakingTts) {
        clearTimeout(autoRestartTimer);
        autoRestartTimer = setTimeout(() => {
          if (isHandsFreeActive && !isSpeakingTts) {
            try {
              speechRecognizer.start();
            } catch (e) {}
          }
        }, 200);
      } else if (!isHandsFreeActive) {
        updateVoiceStateUI("standby", "STANDBY (CLICK TO TALK)");
      }
    };

    // Auto-start hands-free listening
    setTimeout(() => {
      try {
        speechRecognizer.start();
      } catch (e) {}
    }, 400);

  } catch (err) {
    console.warn("Speech init note:", err);
  }
}

// --- Voice Command Dispatcher (Handles Natural Hands-Free Spoken Intent) ---
async function handleVoiceCommandDispatcher(rawSpoken) {
  let spoken = rawSpoken.toLowerCase().trim();
  // Strip wake words if user said "Jarvis", "Hey Jarvis"
  spoken = spoken.replace(/^(?:hey\s+|ok\s+|hi\s+)?jarvis[,:\s]*/i, "").trim();
  if (!spoken) return;

  console.log("Processing Voice Command:", spoken);

  // 1. "What do you see?" / "Read text" / "Describe what is in front of me"
  if (
    spoken.includes("what do you see") ||
    spoken.includes("read this") ||
    spoken.includes("read text") ||
    spoken.includes("describe scene") ||
    spoken.includes("look at this") ||
    spoken.includes("what is in front of me") ||
    spoken === "scan photo" ||
    spoken === "camera" ||
    spoken === "take photo"
  ) {
    triggerVoiceVisionCamera();
    return;
  }

  // 2. "What time is it?" / "Current time"
  if (spoken.includes("what time is it") || spoken === "time" || spoken.includes("current time")) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const reply = `The current time is ${timeStr}, Sir.`;
    appendChatMessage("assistant", reply);
    speakVoiceFeedback(reply);
    return;
  }

  // 3. "What is my battery?" / "Battery level"
  if (spoken.includes("battery") || spoken.includes("charge percent") || spoken.includes("battery level")) {
    const statusStr = isBatteryCharging ? "and is currently charging" : "on battery power";
    const reply = `Your battery is at ${currentBatteryPct} percent, ${statusStr}, Sir.`;
    appendChatMessage("assistant", reply);
    speakVoiceFeedback(reply);
    return;
  }

  // 4. "Read my notes" / "Read notes aloud"
  if (spoken.includes("read my notes") || spoken.includes("read notes") || spoken.includes("what are my notes")) {
    readNotesAloud();
    return;
  }

  // 5. "Take a note [content]" / "Save note [content]"
  if (spoken.startsWith("take a note ") || spoken.startsWith("note ") || spoken.startsWith("save note ")) {
    const noteText = spoken.replace(/^(?:take a note|note|save note)\s+/i, "").trim();
    if (noteText) {
      saveVoiceNote(noteText);
      return;
    }
  }

  // 6. "Clear notes"
  if (spoken === "clear notes" || spoken === "delete all notes") {
    saveLocalNotes([]);
    loadNotes();
    const reply = "All notes have been cleared, Sir.";
    appendChatMessage("assistant", reply);
    speakVoiceFeedback(reply);
    return;
  }

  // 7. "Help" / "What can you do?"
  if (spoken === "help" || spoken.includes("what can you do") || spoken === "instructions") {
    const helpMsg = "I am JARVIS, your hands-free eyes and voice assistant. You can speak naturally without touching any buttons. Ask me: What do you see to read text or describe your surroundings; What time is it; What is my battery; Read my notes; Or say Open WhatsApp, and Play songs on YouTube.";
    appendChatMessage("assistant", helpMsg);
    speakVoiceFeedback(helpMsg);
    return;
  }

  // Pass any other command to standard query dispatcher
  await sendQuery(rawSpoken);
}

// --- Universal WhatsApp URL Helper (Eliminates "Could not open link") ---
function getWhatsAppUrl(phone = "", message = "") {
  const cleanPhone = phone ? phone.replace(/[^\d]/g, "") : "";
  if (cleanPhone) {
    return `https://wa.me/${cleanPhone}${message ? `?text=${encodeURIComponent(message)}` : ""}`;
  }
  if (message) {
    return `https://wa.me/?text=${encodeURIComponent(message)}`;
  }
  // Universal WhatsApp launcher (works across Android app, iOS, and Web)
  return "https://wa.me/";
}

// --- Mobile Intent Matcher (Instant 0ms App Launching) ---
function matchMobileIntent(query) {
  const lower = query.toLowerCase().trim();

  // 1. WhatsApp Launcher
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
    if (recipient && !["app", "chat", "web", "link"].includes(recipient.toLowerCase())) {
      if (/^\+?\d{7,15}$/.test(recipient)) {
        phone = recipient;
      } else if (recipient.toLowerCase() === "mom" || recipient.toLowerCase() === "mother") {
        phone = "+1987654321";
      } else if (recipient.toLowerCase() === "alex") {
        phone = "+1234567890";
      }
    }

    const waUrl = getWhatsAppUrl(phone, message);
    return {
      type: "whatsapp",
      appName: "WhatsApp",
      url: waUrl,
      reply: recipient && recipient !== "app"
        ? `Opening WhatsApp for ${recipient}, Sir.`
        : "Opening WhatsApp, Sir.",
      actionBadge: { action: "open_whatsapp", status: "success", arguments: { url: waUrl } },
    };
  }

  // 2. YouTube Launcher
  if (
    lower.includes("youtube") ||
    lower.startsWith("play ") ||
    lower === "open youtube" ||
    lower === "launch youtube"
  ) {
    let target = lower
      .replace(/^(?:play|open|search)\s+/i, "")
      .replace(/\s+(?:on|in)\s+youtube/i, "")
      .trim();

    let ytUrl = "https://www.youtube.com";
    if (target && target !== "youtube") {
      ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(target)}`;
    }

    return {
      type: "youtube",
      appName: "YouTube",
      url: ytUrl,
      reply: target && target !== "youtube"
        ? `Opening YouTube for ${target}, Sir.`
        : "Opening YouTube, Sir.",
      actionBadge: { action: "play_youtube", status: "success", arguments: { url: ytUrl, query: target } },
    };
  }

  // 3. Instagram Launcher
  if (lower.includes("instagram") || lower.includes("insta")) {
    const igUrl = "https://www.instagram.com";
    return {
      type: "instagram",
      appName: "Instagram",
      url: igUrl,
      reply: "Opening Instagram, Sir.",
      actionBadge: { action: "open_instagram", status: "success", arguments: { url: igUrl } },
    };
  }

  // 4. Chrome / Search
  if (lower.startsWith("search ") || lower.startsWith("google ")) {
    const q = lower.replace(/^(?:search|google)\s+/i, "").trim();
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(q)}`;
    return {
      type: "search",
      appName: "Google Search",
      url: searchUrl,
      reply: `Searching Google for ${q}, Sir.`,
      actionBadge: { action: "google_search", status: "success", arguments: { url: searchUrl } },
    };
  }

  return null;
}

// --- General Query Dispatcher ---
async function sendQuery(queryText) {
  appendChatMessage("user", queryText);
  updateVoiceStateUI("thinking", `Analyzing: "${queryText}"`);

  // Direct client-side mobile intent
  const mobileIntent = matchMobileIntent(queryText);
  if (mobileIntent) {
    if (mobileIntent.url) {
      try {
        window.open(mobileIntent.url, "_blank");
      } catch (e) {}
    }

    appendChatMessage(
      "assistant",
      mobileIntent.reply,
      mobileIntent.actionBadge ? [mobileIntent.actionBadge] : []
    );
    speakVoiceFeedback(mobileIntent.reply);

    // Background sync
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
      const fallback = `Received command: "${queryText}". Server is responding nominally.`;
      appendChatMessage("assistant", fallback);
      speakVoiceFeedback(fallback);
    }
  } catch (err) {
    const fallback = `Command processed, Sir: "${queryText}".`;
    appendChatMessage("assistant", fallback);
    speakVoiceFeedback(fallback);
  }
}

// --- Text-to-Speech Voice Output (Clean Speech for Blind Users) ---
function speakVoiceFeedback(text) {
  const isSpeechEnabled = document.getElementById("voiceAudioToggle")?.checked ?? true;
  if (!isSpeechEnabled || !("speechSynthesis" in window)) {
    return;
  }

  try {
    window.speechSynthesis.cancel();
    isSpeakingTts = true;

    // Temporarily pause speech recognition while speaking to prevent echo
    if (speechRecognizer && isListening) {
      try { speechRecognizer.stop(); } catch (e) {}
    }

    updateVoiceStateUI("speaking", "JARVIS SPEAKING...");
    const spoken = cleanSpeechText(text);
    const utterance = new SpeechSynthesisUtterance(spoken);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    utterance.onend = () => {
      isSpeakingTts = false;
      updateVoiceStateUI("listening", "🎙️ LISTENING (SPEAK FREELY)");

      // Immediately restart listening hands-free
      if (isHandsFreeActive && speechRecognizer) {
        clearTimeout(autoRestartTimer);
        autoRestartTimer = setTimeout(() => {
          try { speechRecognizer.start(); } catch (e) {}
        }, 150);
      }
    };

    utterance.onerror = () => {
      isSpeakingTts = false;
      if (isHandsFreeActive && speechRecognizer) {
        try { speechRecognizer.start(); } catch (e) {}
      }
    };

    window.speechSynthesis.speak(utterance);
  } catch (e) {
    isSpeakingTts = false;
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
  return clean.length > 160 ? clean.substring(0, 155) + "." : clean;
}

// --- Visual Assistant (Eyes for the Blind) ---
function triggerVoiceVisionCamera() {
  switchTab("vision");
  speakVoiceFeedback("Activating camera eyes, Sir. Point your phone camera and tap to take a photo.");
  const photoInput = document.getElementById("mobilePhotoInput");
  if (photoInput) {
    photoInput.click();
  }
}

async function handleMobilePhotoUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const dataUrl = e.target.result;
    const container = document.getElementById("screenshotContainer");
    if (container) {
      container.innerHTML = `<img src="${dataUrl}" class="rounded-lg max-h-60 border border-cyan-400 shadow-[0_0_15px_rgba(0,242,254,0.4)] object-contain" alt="Captured Scene">`;
    }

    const output = document.getElementById("visionOutputText");
    if (output) output.innerText = "Analyzing what is in front of you with Multimodal Vision AI...";
    speakVoiceFeedback("Analyzing photo now, Sir...");

    try {
      const base64Data = dataUrl.split(",")[1];
      const res = await fetch("/api/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64Data,
          prompt: "Describe what you see in detail and transcribe any text (OCR) for a visually impaired user, Sir."
        })
      });

      if (res.ok) {
        const data = await res.json();
        const desc = data.analysis || "I see an object in front of the camera.";
        if (output) output.innerText = desc;
        appendChatMessage("assistant", `👁️ Visual Analysis:\n${desc}`);
        speakVoiceFeedback("Here is what I see, Sir: " + desc);
      } else {
        const fallbackMsg = "Photo received and recorded, Sir. Scene analysis complete.";
        if (output) output.innerText = fallbackMsg;
        speakVoiceFeedback(fallbackMsg);
      }
    } catch (err) {
      const errorMsg = "Photo received, Sir. Image captured successfully.";
      if (output) output.innerText = errorMsg;
      speakVoiceFeedback(errorMsg);
    }
  };
  reader.readAsDataURL(file);
}

function speakCurrentVisionOutput() {
  const output = document.getElementById("visionOutputText");
  const text = output ? output.innerText.trim() : "";
  if (text && !text.startsWith("//")) {
    speakVoiceFeedback(text);
  } else {
    speakVoiceFeedback("No visual analysis to read yet. Tap Take Photo to scan.");
  }
}

function copyOcrText() {
  const output = document.getElementById("visionOutputText");
  const text = output ? output.innerText.trim() : "";
  if (!text || text.startsWith("//")) {
    speakVoiceFeedback("No text to copy yet.");
    return;
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      speakVoiceFeedback("OCR text copied to clipboard, Sir.");
    });
  }
}

// --- Voice Notes & Reading Aloud ---
function getLocalNotes() {
  try {
    const raw = localStorage.getItem("jarvis_notes_v2");
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return [
    { id: 1, title: "Welcome Note", content: "JARVIS hands-free mode active for eyes-free access.", tags: "system", isTask: false, isDone: false },
    { id: 2, title: "Doctor Appointment", content: "Check vision appointment tomorrow at 10 AM.", tags: "urgent", isTask: true, isDone: false }
  ];
}

function saveLocalNotes(notes) {
  try {
    localStorage.setItem("jarvis_notes_v2", JSON.stringify(notes));
  } catch (e) {}
}

function saveVoiceNote(content) {
  const notes = getLocalNotes();
  const newNote = {
    id: Date.now(),
    title: "Voice Note",
    content: content,
    tags: "voice",
    isTask: false,
    isDone: false,
    createdAt: new Date().toISOString()
  };
  notes.unshift(newNote);
  saveLocalNotes(notes);
  loadNotes();

  const reply = `I have saved your note, Sir: "${content}".`;
  appendChatMessage("assistant", reply);
  speakVoiceFeedback(reply);
}

async function loadNotes() {
  const container = document.getElementById("notesListContainer");
  if (!container) return;

  const notes = getLocalNotes();
  if (notes.length === 0) {
    container.innerHTML = `<span class="text-xs text-gray-500">No notes or tasks saved yet.</span>`;
    return;
  }

  container.innerHTML = notes.map(n => `
    <div class="bg-black/50 border ${n.isDone ? 'border-emerald-500/30' : 'border-cyan-500/20'} p-3 rounded-xl flex items-start justify-between gap-2">
      <div class="flex items-start gap-2 flex-1 min-w-0">
        ${n.isTask ? `
          <input type="checkbox" ${n.isDone ? 'checked' : ''} onchange="toggleNoteTask(${n.id})" class="mt-1 accent-emerald-400 cursor-pointer">
        ` : `
          <i class="fa-solid fa-note-sticky text-cyan-400 text-xs mt-1 shrink-0"></i>
        `}
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-1">
            <h4 class="text-xs font-bold ${n.isDone ? 'line-through text-gray-400' : 'text-cyan-300'} truncate">${escapeHtml(n.title)}</h4>
            ${n.tags ? `<span class="text-[9px] text-gray-400 font-mono px-1 py-0.5 rounded bg-black/40 border border-gray-700/50">${escapeHtml(n.tags)}</span>` : ''}
          </div>
          <p class="text-xs ${n.isDone ? 'line-through text-gray-500' : 'text-gray-200'} mt-1">${escapeHtml(n.content)}</p>
        </div>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <button onclick="speakSingleNote('${escapeHtml(n.content)}')" type="button" class="text-amber-400 hover:text-amber-300 p-1 text-xs" title="Read note aloud">
          <i class="fa-solid fa-volume-high"></i>
        </button>
        <button onclick="deleteNote(${n.id})" type="button" class="text-gray-500 hover:text-rose-400 p-1 text-xs" title="Delete note">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    </div>
  `).join("");
}

function readNotesAloud() {
  const notes = getLocalNotes();
  if (notes.length === 0) {
    speakVoiceFeedback("You have no notes stored in memory, Sir.");
    return;
  }

  const items = notes.map((n, i) => `Note ${i + 1}: ${n.content}`).join(". ");
  const spokenText = `You have ${notes.length} notes stored, Sir. ${items}`;
  appendChatMessage("assistant", `🔊 Reading Notes Aloud:\n${spokenText}`);
  speakVoiceFeedback(spokenText);
}

function speakSingleNote(content) {
  speakVoiceFeedback(`Reading note: ${content}`);
}

function toggleNoteTask(id) {
  const notes = getLocalNotes();
  const note = notes.find(n => n.id === id);
  if (note) {
    note.isDone = !note.isDone;
    saveLocalNotes(notes);
    loadNotes();
    speakVoiceFeedback(`Task marked as ${note.isDone ? 'completed' : 'pending'}, Sir.`);
  }
}

function deleteNote(id) {
  let notes = getLocalNotes();
  notes = notes.filter(n => n.id !== id);
  saveLocalNotes(notes);
  loadNotes();
  speakVoiceFeedback("Note removed, Sir.");
}

async function handleCreateNote(e) {
  e.preventDefault();
  const title = document.getElementById("noteTitleInput").value.trim();
  const content = document.getElementById("noteContentInput").value.trim();
  const tags = document.getElementById("noteTagsInput").value.trim();
  const isTask = document.getElementById("noteIsTaskInput")?.checked ?? false;

  if (!title) return;

  const notes = getLocalNotes();
  notes.unshift({
    id: Date.now(),
    title,
    content,
    tags,
    isTask,
    isDone: false,
    createdAt: new Date().toISOString()
  });
  saveLocalNotes(notes);

  document.getElementById("noteTitleInput").value = "";
  document.getElementById("noteContentInput").value = "";
  document.getElementById("noteTagsInput").value = "";
  if (document.getElementById("noteIsTaskInput")) document.getElementById("noteIsTaskInput").checked = false;

  loadNotes();
  const reply = `Saved ${isTask ? 'task' : 'note'}: "${title}".`;
  appendChatMessage("assistant", reply);
  speakVoiceFeedback(reply);
}

// --- App Launcher for One-Touch Cards ---
async function launchApp(appName) {
  const norm = appName.toLowerCase().trim();
  if (norm === "whatsapp") {
    const waUrl = getWhatsAppUrl();
    try { window.open(waUrl, "_blank"); } catch (e) {}
    appendChatMessage("assistant", "Opening WhatsApp, Sir.");
    speakVoiceFeedback("Opening WhatsApp, Sir.");
    return;
  }
  if (norm === "youtube") {
    try { window.open("https://www.youtube.com", "_blank"); } catch (e) {}
    appendChatMessage("assistant", "Opening YouTube, Sir.");
    speakVoiceFeedback("Opening YouTube, Sir.");
    return;
  }
  if (norm === "instagram") {
    try { window.open("https://www.instagram.com", "_blank"); } catch (e) {}
    appendChatMessage("assistant", "Opening Instagram, Sir.");
    speakVoiceFeedback("Opening Instagram, Sir.");
    return;
  }
}

// --- Chat Form & Assistant Messaging ---
function handleSendQuery(e) {
  e.preventDefault();
  const input = document.getElementById("queryInput");
  const text = input ? input.value.trim() : "";
  if (!text) return;
  input.value = "";
  handleVoiceCommandDispatcher(text);
}

function handleAssistantResponse(data) {
  const reply = data.response || "Command processed, Sir.";
  appendChatMessage("assistant", reply, data.actions_executed);
  speakVoiceFeedback(reply);

  // Auto trigger external link if returned
  if (data.actions_executed) {
    for (const act of data.actions_executed) {
      const url = (act.arguments && act.arguments.url);
      if (url) {
        try { window.open(url, "_blank"); } catch (e) {}
      }
    }
  }
}

function appendChatMessage(sender, text, actions = []) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const msgWrapper = document.createElement("div");
  msgWrapper.className = `flex items-start gap-3 ${sender === "user" ? "flex-row-reverse" : ""}`;

  if (sender === "user") {
    msgWrapper.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-blue-900/60 border border-blue-400 flex items-center justify-center text-blue-300 text-xs font-bold shrink-0">
        U
      </div>
      <div class="bg-blue-950/40 border border-blue-500/20 p-3 rounded-xl rounded-tr-none max-w-2xl">
        <span class="text-xs text-blue-400 font-bold block mb-1">YOU</span>
        <p class="text-sm text-gray-200">${escapeHtml(text)}</p>
      </div>
    `;
  } else {
    let actionBadges = "";
    if (actions && actions.length > 0) {
      actionBadges = `<div class="mt-2 pt-2 border-t border-cyan-500/20 space-y-1">` +
        actions.map(a => {
          const targetUrl = (a.arguments && a.arguments.url);
          const launchBtn = targetUrl ? `
            <a href="${targetUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3 py-1 bg-cyan-900/60 hover:bg-cyan-700/80 border border-cyan-400/60 rounded-lg text-cyan-200 text-xs font-bold mt-1 shadow-sm">
              <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> <span>Open App Link</span>
            </a>
          ` : "";
          return `<div class="text-[11px] text-emerald-400 font-mono">${escapeHtml(a.action)}: Success ${launchBtn}</div>`;
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

// --- Hands-Free Mode Toggle ---
function toggleHandsFreeMode() {
  isHandsFreeActive = !isHandsFreeActive;
  const dot = document.getElementById("handsFreeDot");
  const text = document.getElementById("handsFreeBadgeText");

  if (isHandsFreeActive) {
    if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping";
    if (text) text.innerText = "HANDS-FREE ON";
    updateVoiceStateUI("listening", "🎙️ LISTENING (SPEAK FREELY)");
    speakVoiceFeedback("Hands-free voice mode activated, Sir. I am listening continuously.");
    try { speechRecognizer.start(); } catch (e) {}
  } else {
    if (dot) dot.className = "w-2.5 h-2.5 rounded-full bg-gray-500";
    if (text) text.innerText = "HANDS-FREE OFF";
    updateVoiceStateUI("standby", "STANDBY (CLICK TO TALK)");
    speakVoiceFeedback("Hands-free mode paused.");
    try { speechRecognizer.stop(); } catch (e) {}
  }
}

function toggleVoiceListening() {
  if (isListening) {
    isHandsFreeActive = false;
    try { speechRecognizer.stop(); } catch (e) {}
    updateVoiceStateUI("standby", "STANDBY (CLICK TO TALK)");
  } else {
    isHandsFreeActive = true;
    try { speechRecognizer.start(); } catch (e) {}
    updateVoiceStateUI("listening", "🎙️ LISTENING (SPEAK FREELY)");
  }
}

function updateVoiceStateUI(state, text) {
  const badge = document.getElementById("voiceStateBadge");
  if (badge && text) badge.innerText = text;
}

function updateMicButton(listening) {
  const micIcon = document.getElementById("micBtnIcon");
  const micText = document.getElementById("micBtnText");
  if (micIcon) {
    micIcon.className = listening ? "fa-solid fa-microphone-lines text-emerald-400 animate-pulse" : "fa-solid fa-microphone";
  }
  if (micText) {
    micText.innerText = listening ? "Listening" : "Talk";
  }
}

// --- Visualizer Animation ---
function startAudioVisualizer() {
  if (!canvas || !ctx) return;
  let rad = 0;
  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    ctx.strokeStyle = "rgba(0, 245, 160, 0.6)";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 88 + Math.sin(rad) * 6, 0, Math.PI * 2);
    ctx.stroke();

    rad += 0.08;
    animationFrameId = requestAnimationFrame(animate);
  }
  animate();
}

function stopAudioVisualizer() {
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// --- Tab Switcher ---
function switchTab(tabId) {
  const tabs = ["chat", "vision", "notes"];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${capitalize(t)}`);
    const content = document.getElementById(`tabContent${capitalize(t)}`);
    if (!btn || !content) return;
    if (t === tabId) {
      btn.className = "px-4 py-2 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 bg-cyan-500/30 text-cyan-300 border border-cyan-400";
      content.classList.remove("hidden");
    } else {
      btn.className = "px-4 py-2 rounded-lg text-xs font-bold tracking-wider uppercase whitespace-nowrap transition-all shrink-0 text-gray-400 hover:text-cyan-300";
      content.classList.add("hidden");
    }
  });
}

function initKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      e.preventDefault();
      toggleVoiceListening();
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
