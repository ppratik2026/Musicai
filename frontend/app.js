/* MusicAI Studio frontend */

const $ = (sel) => document.querySelector(sel);

const state = {
  engines: [],
  tracks: [],
  pollTimer: null,
};

/* ---------- engines ---------- */

async function loadEngines() {
  const res = await fetch("/api/engines");
  const data = await res.json();
  state.engines = data.engines;

  const select = $("#engine");
  select.innerHTML = '<option value="auto">Auto (best available)</option>';
  for (const e of data.engines) {
    const opt = document.createElement("option");
    opt.value = e.name;
    opt.textContent = e.display_name + (e.available ? "" : " — not installed");
    opt.disabled = !e.available;
    select.appendChild(opt);
  }

  const available = data.engines.filter((e) => e.available);
  const best = available.find((e) => e.name === "ace_step") || available[0];
  $("#engine-status").textContent = best
    ? `engine ready: ${best.display_name}`
    : "no engine available";
  updateEngineNote();
}

function updateEngineNote() {
  const name = $("#engine").value;
  const engine = state.engines.find((e) => e.name === name);
  const note = $("#engine-note");
  if (!engine) {
    note.textContent =
      "Auto picks the best installed engine (ACE-Step → MusicGen → demo synth).";
    return;
  }
  note.textContent =
    `${engine.description} License: ${engine.license}. ` +
    (engine.commercial_use
      ? "✅ Commercial release allowed."
      : "⚠️ Non-commercial weights — don't sell/distribute these tracks.");
}

/* ---------- generation ---------- */

async function generate() {
  const prompt = $("#prompt").value.trim();
  if (!prompt) {
    $("#prompt").focus();
    return;
  }
  const btn = $("#generate-btn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        lyrics: $("#lyrics").value,
        title: $("#title").value || "Untitled",
        artist: $("#artist").value,
        duration: Number($("#duration").value),
        engine: $("#engine").value,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Generation request failed");
      return;
    }
    await refreshTracks();
  } finally {
    btn.disabled = false;
  }
}

/* ---------- library ---------- */

async function refreshTracks() {
  const res = await fetch("/api/tracks");
  const data = await res.json();
  state.tracks = data.tracks;
  renderTracks();

  const busy = state.tracks.some((t) => t.status === "queued" || t.status === "generating");
  clearTimeout(state.pollTimer);
  if (busy) state.pollTimer = setTimeout(refreshTracks, 2500);
}

function fmtDuration(s) {
  if (!s) return "";
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function renderTracks() {
  const wrap = $("#tracks");
  $("#empty-state").style.display = state.tracks.length ? "none" : "block";
  wrap.innerHTML = "";

  for (const t of state.tracks) {
    const el = document.createElement("div");
    el.className = "track";

    const sub = [t.artist, t.engine, fmtDuration(t.duration)].filter(Boolean).join(" · ");
    el.innerHTML = `
      <div class="track-head">
        <div>
          <div class="track-title"></div>
          <div class="track-sub"></div>
        </div>
        <span class="status ${t.status}">${t.status}</span>
      </div>`;
    el.querySelector(".track-title").textContent = t.title;
    el.querySelector(".track-sub").textContent = sub || t.prompt.slice(0, 60);

    if (t.status === "queued" || t.status === "generating") {
      el.insertAdjacentHTML("beforeend", '<div class="progress"></div>');
    }

    if (t.status === "error") {
      const err = document.createElement("div");
      err.className = "track-error";
      err.textContent = t.error;
      el.appendChild(err);
    }

    if (t.status === "done") {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = `/api/tracks/${t.id}/audio`;
      el.appendChild(audio);
    }

    const actions = document.createElement("div");
    actions.className = "track-actions";

    if (t.status === "done") {
      for (const fmt of ["wav", "mp3", "flac"]) {
        const a = document.createElement("a");
        a.className = "btn";
        a.href = `/api/tracks/${t.id}/download?fmt=${fmt}`;
        a.textContent = `⬇ ${fmt.toUpperCase()}`;
        actions.appendChild(a);
      }
      const cover = document.createElement("button");
      cover.className = "btn";
      cover.textContent = t.cover_path ? "🖼 Cover ✓" : "🖼 Cover art";
      cover.onclick = () => uploadCover(t.id);
      actions.appendChild(cover);
    }

    if (t.status === "error") {
      const retry = document.createElement("button");
      retry.className = "btn";
      retry.textContent = "↻ Retry";
      retry.onclick = async () => {
        await fetch(`/api/tracks/${t.id}/retry`, { method: "POST" });
        refreshTracks();
      };
      actions.appendChild(retry);
    }

    const del = document.createElement("button");
    del.className = "btn danger";
    del.textContent = "✕ Delete";
    del.onclick = async () => {
      if (!confirm(`Delete "${t.title}"?`)) return;
      await fetch(`/api/tracks/${t.id}`, { method: "DELETE" });
      refreshTracks();
    };
    actions.appendChild(del);

    el.appendChild(actions);
    wrap.appendChild(el);
  }
}

function uploadCover(trackId) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/jpeg,image/png";
  input.onchange = async () => {
    if (!input.files.length) return;
    const form = new FormData();
    form.append("file", input.files[0]);
    await fetch(`/api/tracks/${trackId}/cover`, { method: "POST", body: form });
    refreshTracks();
  };
  input.click();
}

/* ---------- wiring ---------- */

$("#generate-btn").addEventListener("click", generate);
$("#engine").addEventListener("change", updateEngineNote);
$("#duration").addEventListener("input", () => {
  $("#duration-label").textContent = `${$("#duration").value}s`;
});
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    $("#prompt").value = chip.dataset.tag;
    $("#prompt").focus();
  });
});

loadEngines();
refreshTracks();
