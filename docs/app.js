/* Dynamic Island for Windows – interactive design preview.
 * Plain JS, no dependencies, no network, no trackers. All data below is made up. */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const island = $("#island"), row = $("#row");
  const params = new URLSearchParams(location.search);
  const pad = (n) => String(n).padStart(2, "0");
  const mmss = (s) => `${Math.floor(s / 60)}:${pad(Math.floor(s % 60))}`;

  const TRACKS = [
    { t: "Sample Track", a: "Sample Artist", d: 200 },
    { t: "Placeholder Groove", a: "Example Band", d: 187 },
    { t: "Demo Sunrise", a: "Test Ensemble", d: 242 },
  ];
  const ALERTS = [
    { r: "AAA → BBB", w: "12 Mar – 19 Mar · round trip", p: 189, was: 240, s: [9, 8, 8.5, 7, 6.5, 5, 3] },
    { r: "CCC → DDD", w: "02 Apr – 09 Apr · round trip", p: 312, was: 365, s: [6, 6.5, 6, 5.5, 4.5, 4, 3.5] },
    { r: "EEE → FFF", w: "20 May · one way", p: 74, was: 99, s: [8, 7.5, 8, 6, 5.5, 4, 2.5] },
  ];
  const S = {
    state: "idle", expanded: false,
    timer: { total: 25 * 60, left: 25 * 60, running: true },
    music: { i: 0, pos: 0, playing: true },
    call: { status: "ringing", secs: 0, muted: false },
    alert: 0,
  };

  /* ---------- rendering ---------- */
  function renderClock() {
    const d = new Date();
    $$("[data-clock]").forEach((e) => (e.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}`));
    $("[data-clock-big]").textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    $("[data-date]").textContent = d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
  }
  function renderTimer() {
    const { total, left } = S.timer, f = 1 - left / total;
    const C = 2 * Math.PI * 52, c = 2 * Math.PI * 9;
    const ring = $("[data-ring]"), mini = $("[data-mini-ring]");
    ring.style.strokeDasharray = C; ring.style.strokeDashoffset = C * (1 - f);
    mini.style.strokeDasharray = c; mini.style.strokeDashoffset = c * (1 - f);
    $("[data-timer-text]").textContent = mmss(left);
    $("[data-timer-big]").textContent = mmss(left);
    $("[data-timer-toggle]").textContent = S.timer.running ? "Pause" : "Resume";
  }
  function renderMusic() {
    const tr = TRACKS[S.music.i];
    $("[data-track-title]").textContent = tr.t;
    $("[data-track-artist]").textContent = tr.a;
    $("[data-music-line]").textContent = `${tr.t} — ${tr.a}`;
    $("[data-progress]").style.width = `${(S.music.pos / tr.d) * 100}%`;
    $("[data-pos]").textContent = mmss(S.music.pos);
    $("[data-dur]").textContent = mmss(tr.d);
    island.dataset.paused = S.music.playing ? "0" : "1";
    $("[data-play] svg").innerHTML = S.music.playing ? '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>' : '<path d="M7 4.5v15l12-7.5z"/>';
  }
  function renderCall() {
    const c = S.call, on = c.status === "active";
    island.dataset.oncall = on ? "1" : "0";
    island.dataset.ringing = c.status === "ringing" ? "1" : "0";
    const txt = c.status === "ringing" ? "Incoming call…" : `On call · ${mmss(c.secs)}`;
    $("[data-call-status]").textContent = txt;
    $("[data-call-sub]").textContent = c.status === "ringing" ? "Incoming call" : `On call · ${mmss(c.secs)}`;
    $("[data-mute]").textContent = c.muted ? "Unmute" : "Mute";
  }
  function renderFlight() {
    const a = ALERTS[S.alert], drop = Math.round((1 - a.p / a.was) * 100);
    $("[data-flight-line]").textContent = `${a.r} · $${a.p}`;
    $("[data-flight-route]").textContent = a.r;
    $("[data-flight-when]").textContent = a.w;
    $("[data-flight-price]").textContent = `$${a.p}`;
    $("[data-flight-was]").textContent = `$${a.was}`;
    $("[data-flight-drop]").textContent = `-${drop}%`;
    $("[data-flight-drop2]").textContent = `-${drop}%`;
    $("[data-spark]").setAttribute("points", a.s.map((v, i) => `${(i / (a.s.length - 1)) * 200},${40 - v * 4}`).join(" "));
  }
  function renderAll() { renderClock(); renderTimer(); renderMusic(); renderCall(); renderFlight(); }

  /* ---------- state ---------- */
  function setState(name, expanded) {
    if (name === "call" && S.state !== "call") S.call = { status: "ringing", secs: 0, muted: false };
    if (name === "timer" && S.state !== "timer") S.timer = { total: 25 * 60, left: 25 * 60, running: true };
    S.state = name;
    if (typeof expanded === "boolean") S.expanded = expanded;
    island.dataset.state = name;
    island.classList.toggle("expanded", S.expanded);
    row.setAttribute("aria-expanded", String(S.expanded));
    $$(".states button").forEach((b) => b.classList.toggle("active", b.dataset.state === name));
    renderAll();
  }
  const toggle = () => setState(S.state, !S.expanded);

  /* ---------- events ---------- */
  row.addEventListener("click", (e) => { if (!e.target.closest("button")) toggle(); });
  row.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); toggle(); } });
  $$(".states button").forEach((b) => b.addEventListener("click", () => setState(b.dataset.state, true)));
  document.addEventListener("keydown", (e) => {
    const k = { 1: "idle", 2: "call", 3: "timer", 4: "music", 5: "flight" }[e.key];
    if (k) return setState(k, true);
    if (e.key === " " && !e.target.closest("button")) { e.preventDefault(); toggle(); }
    if (e.key === "Escape") setState(S.state, false);
  });
  const actions = {
    "call-accept": () => { S.call = { status: "active", secs: 0, muted: false }; setState("call", S.expanded); },
    "call-end": () => setState("idle", false),
    mute: () => { S.call.muted = !S.call.muted; renderCall(); },
    "timer-toggle": () => { S.timer.running = !S.timer.running; renderTimer(); },
    "timer-reset": () => { S.timer.left = S.timer.total; S.timer.running = true; renderTimer(); },
    play: () => { S.music.playing = !S.music.playing; renderMusic(); },
    next: () => { S.music.i = (S.music.i + 1) % TRACKS.length; S.music.pos = 0; renderMusic(); },
    prev: () => { S.music.i = (S.music.i + TRACKS.length - 1) % TRACKS.length; S.music.pos = 0; renderMusic(); },
    "flight-next": () => { S.alert = (S.alert + 1) % ALERTS.length; renderFlight(); },
    "flight-dismiss": () => setState("idle", false),
  };
  $$("[data-act]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); actions[b.dataset.act](); }));

  /* ---------- 1 s tick ---------- */
  setInterval(() => {
    if (S.timer.running && S.timer.left > 0) S.timer.left -= 1;
    const tr = TRACKS[S.music.i];
    if (S.music.playing) { S.music.pos += 1; if (S.music.pos >= tr.d) actions.next(); }
    if (S.call.status === "active") S.call.secs += 1;
    renderAll();
  }, 1000);

  /* ---------- public hooks (used to record the README GIF) ---------- */
  window.demo = { setState, toggle };
  if (params.has("capture")) document.body.classList.add("capture");

  setState(params.get("state") || "idle", params.get("expanded") === "1");

  if (params.has("autoplay")) {
    // ~6 s scripted loop: idle -> call -> timer -> music -> flight alert -> idle
    const steps = [
      [0, () => setState("idle", false)],
      [600, () => setState("call", false)],
      [1500, () => { actions["call-accept"](); setState("call", true); }],
      [2400, () => setState("timer", true)],
      [3400, () => setState("music", true)],
      [4400, () => setState("flight", false)],
      [4900, () => setState("flight", true)],
      [5800, () => setState("idle", false)],
    ];
    const run = () => steps.forEach(([t, f]) => setTimeout(f, t));
    run(); setInterval(run, 6400);
  }
})();
