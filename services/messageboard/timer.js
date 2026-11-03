"use strict";
const $ = id => document.getElementById(id);
let state = null, busy = false, connected = false, previewKey = "", pollBusy = false;
function payload() { return {text:$("message").value, duration:$("duration").value}; }
function key() { return JSON.stringify(payload()); }
function image(id, data) { if (data) {$(id).src = "data:image/png;base64," + data; $(id).hidden = false;} }
function controls() {
 const active = !!state?.active;
 $("message").disabled = $("duration").disabled = busy || active;
 $("preview-timer").disabled = busy || active;
 $("start").disabled = busy || active || !connected || !state?.configured || previewKey !== key();
 $("cancel").disabled = busy || !active;
}
async function request(path, body) {
 const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 90000);
 try {
  const response = await fetch(path, {cache:"no-store", signal:controller.signal, ...(body === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not update the timer.");
  return data;
 } finally {clearTimeout(timeout);}
}
function show(data) {
 if (state?.active && !data.active) {previewKey = ""; $("screen").hidden = true; $("preview-description").textContent = "Timer finished. Preview again to start another.";}
 state = data; connected = true;
 $("connection").textContent = data.configured ? "Connected at home" : "Device setup needed";
 $("connection").className = data.configured ? "connection online" : "connection";
 $("status-title").textContent = data.active ? data.phase === "finishing" ? "Time to celebrate!" : "Counting down" : "Ready when you are";
 $("status-text").textContent = data.active ? data.text + (data.phase === "finishing" ? " · Other content resumes in about " + Math.max(0,Math.ceil(data.release_at - data.server_now)) + " seconds." : " · " + new Date(data.ends_at * 1000).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"}) + " finish.") : "The timer is idle. Other content can rotate normally.";
 $("preview-label").textContent = data.active ? "LIVE TIMER" : "PREVIEW";
 if (data.active) image("screen", data.image);
 if (data.error) $("feedback").textContent = data.error;
 else if (!data.configured) $("feedback").textContent = "Preview works now. To start on the display, configure the Pi's Tronbyt connection (the same settings as Spin the Wheel).";
 controls();
}
async function refresh() {
 if (busy || pollBusy) return;
 pollBusy = true;
 try {show(await request("/api/timer"));}
 catch {connected = false; $("connection").textContent = "Connection unavailable"; controls();}
 finally {pollBusy = false;}
}
$("preview-timer").addEventListener("click", async () => {
 busy = true; controls(); $("feedback").textContent = "Preparing preview…";
 try {
  const data = await request("/api/timer/preview", payload());
  image("screen",data.image); image("finish-screen",data.finish_image); previewKey = key();
  $("preview-description").textContent = data.lines.length + " line" + (data.lines.length === 1 ? "" : "s") + " · Starts at " + data.clock + ". The countdown updates every second.";
  $("feedback").textContent = "Preview ready. Start when you are ready.";
 } catch(error) {previewKey = ""; $("feedback").textContent = error.message;}
 finally {busy = false; controls();}
});
async function action(path, body) {
 if (busy) return;
 busy = true; controls();
 $("feedback").textContent = path.endsWith("start") ? "Preparing your display…" : "Restoring other content…";
 try {show(await request(path, body)); previewKey = ""; $("feedback").textContent = path.endsWith("start") ? "Timer started. You can close this page." : "Timer cancelled.";}
 catch(error) {connected = false; $("feedback").textContent = error.name === "AbortError" ? "Checking whether the action completed. Please wait before trying again…" : error.message;}
 finally {busy = false; controls(); await refresh();}
}
$("timer-form").addEventListener("submit", event => {event.preventDefault(); if (!$("start").disabled) action("/api/timer/start", payload());});
$("cancel").addEventListener("click", () => action("/api/timer/cancel", {id:state.id}));
for (const id of ["message","duration"]) {
 try {$(id).value = localStorage.getItem("timer-" + id) || $(id).value;} catch {}
 $(id).addEventListener("input", () => {previewKey = ""; $("preview-description").textContent = "Message or duration changed. Preview again before starting."; try {localStorage.setItem("timer-" + id,$(id).value);} catch {} controls();});
}
refresh(); setInterval(refresh, 1000);
