let currentSessionId = null;
let timerInterval = null;
let debateStartTime = null;

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
    loadKeys();
    loadModels();

    document.getElementById("settings-toggle").addEventListener("click", toggleSettings);
    document.getElementById("save-keys").addEventListener("click", saveKeys);
    document.getElementById("start-debate").addEventListener("click", startDebate);
    document.getElementById("stop-debate").addEventListener("click", stopDebate);
    document.getElementById("export-debate").addEventListener("click", exportDebate);
});

// --- Settings ---
function toggleSettings() {
    const panel = document.getElementById("settings-panel");
    panel.classList.toggle("hidden");
}

async function loadKeys() {
    const res = await fetch("/api/keys");
    const data = await res.json();
    for (const [provider, configured] of Object.entries(data)) {
        const dot = document.getElementById(`status-${provider}`);
        if (dot) dot.classList.toggle("active", configured);
    }
}

async function saveKeys() {
    const body = {};
    for (const provider of ["openai", "anthropic", "google"]) {
        const val = document.getElementById(`key-${provider}`).value.trim();
        if (val) body[provider] = val;
    }

    const res = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    for (const [provider, configured] of Object.entries(data.configured)) {
        const dot = document.getElementById(`status-${provider}`);
        if (dot) dot.classList.toggle("active", configured);
    }

    // Clear inputs after save
    for (const provider of ["openai", "anthropic", "google"]) {
        document.getElementById(`key-${provider}`).value = "";
    }

    // Reload models to update which are selectable
    loadModels();
}

// --- Models ---
async function loadModels() {
    const [modelsRes, keysRes] = await Promise.all([
        fetch("/api/models"),
        fetch("/api/keys"),
    ]);
    const models = await modelsRes.json();
    const keys = await keysRes.json();

    const container = document.getElementById("model-checkboxes");
    container.innerHTML = "";

    const providerLabels = { openai: "OpenAI", anthropic: "Anthropic", google: "Google" };

    for (const [provider, modelList] of Object.entries(models)) {
        const group = document.createElement("div");
        group.className = "provider-group";

        const title = document.createElement("h4");
        title.textContent = providerLabels[provider] || provider;
        group.appendChild(title);

        if (!keys[provider]) {
            const note = document.createElement("div");
            note.className = "not-configured";
            note.textContent = "API key not configured";
            group.appendChild(note);
        } else {
            for (const model of modelList) {
                const option = document.createElement("label");
                option.className = "model-option";

                const cb = document.createElement("input");
                cb.type = "checkbox";
                cb.dataset.provider = provider;
                cb.dataset.model = model;

                const span = document.createElement("span");
                span.textContent = model;

                option.appendChild(cb);
                option.appendChild(span);
                group.appendChild(option);
            }
        }

        container.appendChild(group);
    }
}

// --- Debate ---
async function startDebate() {
    const prompt = document.getElementById("prompt-input").value.trim();
    if (!prompt) return alert("Enter a prompt first.");

    const checkboxes = document.querySelectorAll("#model-checkboxes input[type=checkbox]:checked");
    if (checkboxes.length < 2) return alert("Select at least 2 models.");

    const models = Array.from(checkboxes).map(cb => ({
        provider: cb.dataset.provider,
        model: cb.dataset.model,
    }));

    const timeoutMin = parseInt(document.getElementById("timeout-input").value) || 10;

    const res = await fetch("/api/debate/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt,
            models,
            timeout_seconds: timeoutMin * 60,
        }),
    });

    if (!res.ok) {
        const err = await res.json();
        return alert(err.detail || "Failed to start debate");
    }

    const data = await res.json();
    currentSessionId = data.session_id;

    // Switch to debate view
    document.getElementById("prompt-section").classList.add("hidden");
    document.getElementById("debate-section").classList.remove("hidden");

    // Setup columns
    const columns = document.getElementById("debate-columns");
    columns.innerHTML = "";
    for (const m of models) {
        const col = document.createElement("div");
        col.className = "model-column";
        col.id = `col-${m.model}`;
        col.innerHTML = `
            <div class="model-column-header">${m.model}</div>
            <div class="model-column-body" id="body-${m.model}"></div>
        `;
        columns.appendChild(col);
    }

    // Reset state
    document.getElementById("consensus-banner").classList.add("hidden");
    document.getElementById("export-debate").disabled = true;
    document.getElementById("stop-debate").disabled = false;
    setStatus("running", "Running");

    // Start timer
    debateStartTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);

    // Connect to SSE
    connectSSE(currentSessionId);
}

function connectSSE(sessionId) {
    const source = new EventSource(`/api/debate/${sessionId}/stream`);

    source.onmessage = (e) => {
        const event = JSON.parse(e.data);

        switch (event.type) {
            case "initial_response":
                appendResponse(event.model, "Initial Response", event.content);
                break;

            case "debate_turn":
                appendResponse(event.model, `Round ${event.round}`, event.content);
                break;

            case "status":
                // Informational status update — no-op in columns
                break;

            case "consensus":
                setStatus("consensus", "Consensus");
                document.getElementById("consensus-banner").classList.remove("hidden");
                document.getElementById("consensus-content").textContent = event.summary;
                break;

            case "timeout":
                setStatus("timeout", "Timeout");
                showNotification(event.message);
                break;

            case "error":
                setStatus("error", "Error");
                showNotification(event.message);
                break;

            case "done":
                source.close();
                clearInterval(timerInterval);
                document.getElementById("export-debate").disabled = false;
                document.getElementById("stop-debate").disabled = true;
                break;
        }
    };

    source.onerror = () => {
        source.close();
        clearInterval(timerInterval);
        document.getElementById("stop-debate").disabled = true;
    };
}

function appendResponse(model, roundLabel, content) {
    const body = document.getElementById(`body-${model}`);
    if (!body) return;

    const label = document.createElement("div");
    label.className = "round-label";
    label.textContent = roundLabel;

    const bubble = document.createElement("div");
    bubble.className = "response-bubble";
    if (content.startsWith("[ERROR")) bubble.classList.add("error");
    bubble.textContent = content;

    body.appendChild(label);
    body.appendChild(bubble);
    body.scrollTop = body.scrollHeight;
}

function setStatus(cls, text) {
    const badge = document.getElementById("debate-status");
    badge.className = `status-badge ${cls}`;
    badge.textContent = text;
}

function updateTimer() {
    if (!debateStartTime) return;
    const elapsed = Math.floor((Date.now() - debateStartTime) / 1000);
    const min = Math.floor(elapsed / 60).toString().padStart(2, "0");
    const sec = (elapsed % 60).toString().padStart(2, "0");
    document.getElementById("debate-timer").textContent = `${min}:${sec}`;
}

function showNotification(message) {
    // Show as a temporary banner above consensus area
    const banner = document.getElementById("consensus-banner");
    banner.classList.remove("hidden");
    banner.style.background = "#78350f";
    banner.style.borderColor = "#fbbf24";
    banner.querySelector("h3").textContent = "Debate Ended";
    banner.querySelector("h3").style.color = "#fbbf24";
    document.getElementById("consensus-content").textContent = message;
}

async function stopDebate() {
    if (!currentSessionId) return;
    await fetch(`/api/debate/${currentSessionId}/stop`, { method: "POST" });
    setStatus("stopped", "Stopped");
    document.getElementById("stop-debate").disabled = true;
}

async function exportDebate() {
    if (!currentSessionId) return;
    window.location.href = `/api/debate/${currentSessionId}/export`;
}
