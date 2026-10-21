"use strict";
const $ = id => document.getElementById(id);
let state = null;
let busy = false;
let pending = false;
function choices() {return $("labels").value.split(/\r?\n/u).map(s => s.trim()).filter(Boolean);}
try { $("labels").value = localStorage.getItem("wheel-labels") || ""; } catch {}
function controls() {
 const labels = choices();
 $("spin").disabled = busy || pending || !state?.configured || state?.active || labels.length < 2 || labels.length > 12 || labels.some(s => s.length > 20);
 $("labels").disabled = busy || pending || !!state?.active;
 $("done").disabled = busy || !state?.active;
}
function show(data) {
 state = data;
 $("connection").textContent = data.configured ? "Connected at home" : "Device setup needed";
 $("connection").className = data.configured ? "connection online" : "connection";
 $("round-title").textContent = data.active ? (data.winner === null ? "Watch the Tidbyt" : "The wheel has chosen") : "Ready for another round";
 $("result").textContent = data.active ? (data.winner === null ? "Your wheel is on its way to the display…" : data.labels[data.winner]) : data.winner != null ? "Last winner: " + data.labels[data.winner] : "Add your labels, then look at the Tidbyt.";
 $("timing").textContent = data.active ? "Normal content is paused. Automatic return in about " + Math.max(0, Math.ceil(data.release_at - Date.now()/1000)) + " seconds." : "The wheel spins for 8 seconds, then holds the winner. Other content resumes after Done or the timeout.";
 if (data.error || !data.configured) $("feedback").textContent = data.error || "Connect this service to your Tronbyt device on the Pi before spinning.";
 controls();
}
async function request(path, payload) {
 const controller = new AbortController();
 const timer = setTimeout(() => controller.abort(), 90000);
 try {
  const response = await fetch(path, {cache:"no-store", signal:controller.signal, ...(payload === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not update the wheel.");
  return data;
 } finally {clearTimeout(timer);}
}
async function refresh() {
 if (busy) return;
 try { show(await request("/api/wheel")); pending = false; controls(); }
 catch { $("connection").textContent = "Connection unavailable"; }
}
async function action(path, payload) {
 if (busy) return;
 busy = true; controls();
 $("feedback").textContent = path.endsWith("spin") ? "Preparing your wheel…" : "Restoring normal content…";
 try { show(await request(path, payload)); $("feedback").textContent = path.endsWith("spin") ? "Sent to the display. Look at your Tidbyt!" : "Normal content can resume."; }
 catch (error) { pending = error.name === "AbortError"; $("feedback").textContent = pending ? "Checking whether the display received your round. Please wait…" : error.message; }
 finally { busy = false; controls(); await refresh(); }
}
$("labels").addEventListener("input", () => {try {localStorage.setItem("wheel-labels", $("labels").value);} catch {} controls();});
$("wheel-form").addEventListener("submit", e => {e.preventDefault(); if (!$("spin").disabled) action("/api/wheel/spin", {labels:choices()});});
$("done").addEventListener("click", () => action("/api/wheel/done", {id:state.id}));
refresh(); setInterval(refresh, 1000);
