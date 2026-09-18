"use strict";
const $ = (id) => document.getElementById(id);
const palette = {white:"#ffffff",green:"#66ff66",yellow:"#ffdd66",pink:"#ff88bb"};
const flowerMode = location.pathname === "/flowers";
const messageEndpoint = flowerMode ? "/api/flowers" : "/api/message";
const clearEndpoint = flowerMode ? "/api/flowers/clear" : "/api/clear";
let previewTimer = null;
let busy = false;
let lastSaved = null;
let editingId = null;
const nyFormat = new Intl.DateTimeFormat("en-US", {timeZone:"America/New_York",month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"});
function dateLabel(stamp) { return nyFormat.format(new Date(stamp*1000)); }
function localInput(stamp) {
 const parts=new Intl.DateTimeFormat("sv-SE",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date(stamp*1000));
 const values=Object.fromEntries(parts.map(p=>[p.type,p.value]));
 return values.year+"-"+values.month+"-"+values.day+"T"+values.hour+":"+values.minute;
}
function normalized() { return $("message").value.normalize("NFC").replace(/[‘’]/gu,"'").replace(/[“”]/gu,'"').replace(/[–—]/gu,"-").replace(/…/gu,"...").replace(/\s+/gu," ").trim(); }
function valid(text) { return text.length > 0 && text.length <= 120 && /^[\x20-\x7e\xa0-\xff]+$/u.test(text); }
function feedback(message,error=false) { $("feedback").textContent=message; $("feedback").className=error?"error":"success"; }
function draft() {
 const text=normalized();
 $("counter").textContent=text.length+" / 120";
 renderPreview(text);
 $("send").disabled=busy||!valid(text);
 if(text&&!valid(text)) feedback("Use letters, numbers and simple punctuation. Swedish letters work; emoji do not.",true);
 else if(!busy) feedback("");
}
function renderPreview(text) {
 clearInterval(previewTimer);
 const container = $("preview-pages");
 container.replaceChildren();
 if (text && !valid(text)) {
  $("page-count").textContent = "Correct the unsupported characters to preview your message.";
  return;
 }
 if (flowerMode) {
  previewTimer = flowerPreview(text, palette[document.querySelector('input[name="color"]:checked').value]);
  return;
 }
 const lines = boardLines(text);
 const total = Math.max(1, Math.ceil(lines.length / 3));
 const color = palette[document.querySelector('input[name="color"]:checked').value];
 for (let page=0;page<total;page++) {
  const canvas = document.createElement("canvas");
  canvas.width=64; canvas.height=32; canvas.className="pixel-preview";
  const pageLines=lines.slice(page*3,page*3+3);
  canvas.setAttribute("role","img");
  canvas.setAttribute("aria-label","Page "+(page+1)+": "+pageLines.join(" / "));
  const ctx=canvas.getContext("2d");
  ctx.fillStyle="#000000";ctx.fillRect(0,0,64,32);
  for (const [x,y,active] of boardPixels(pageLines,page,total)) {
   ctx.fillStyle=active?color:"#222222";ctx.fillRect(x,y,1,1);
  }
  const label=document.createElement("p");
  label.className="preview-hint";label.textContent="Page "+(page+1)+" of "+total;
  container.append(canvas,label);
 }
 $("page-count").textContent = !text ? "Write a message to check its fit." :
  total===1 ? "Fits on one page · "+lines.length+" of 3 lines used." :
  total+" pages · "+lines.length+" lines. Shorten to 3 lines to keep it on one page.";
}
function showSaved(data) {
 lastSaved=data;
 $("saved-message").textContent=data.active?data.text:data.expired?"Your message has expired.":"The board is clear.";
 $("active-indicator").classList.toggle("active",data.active);
 $("saved-info").textContent=data.active?(data.expires_at?"Expires "+dateLabel(data.expires_at):"Stays until you clear or replace it."):"Send a note whenever you’re ready.";
 $("clear").disabled=busy||!data.active;
 showSchedules(data.schedules||[]);
}
function setMode() {
 const planned=$("mode").value==="schedule";
 $("schedule-fields").hidden=!planned;
 $("now-fields").hidden=planned;
 $("start").required=planned; $("end").required=planned;
 $("stop-edit").hidden=!editingId;
 $("send").textContent=planned?(editingId?"Save changes":"Schedule message"):"Send to display";
}
function showSchedules(items) {
 const container=$("schedules");container.replaceChildren();
 if(!items.length){const p=document.createElement("p");p.className="hint";p.textContent="No upcoming messages.";container.append(p);}
 for(const item of items){
  const row=document.createElement("div");row.className="schedule-item";
  const text=document.createElement("p");text.textContent=item.text;
  const dates=document.createElement("p");dates.className="hint";dates.textContent=dateLabel(item.starts_at)+" → "+dateLabel(item.expires_at);
  const edit=document.createElement("button");edit.type="button";edit.className="secondary";edit.textContent="Edit";edit.disabled=busy;
  edit.addEventListener("click",()=>{
   if(busy)return;
   editingId=item.id;$("message").value=item.text;
   document.querySelector('input[name="color"][value="'+item.color+'"]').checked=true;
   $("start").value=localInput(item.starts_at);$("end").value=localInput(item.expires_at);
   $("mode").value="schedule";setMode();draft();$("message").focus();
  });
  const cancel=document.createElement("button");cancel.type="button";cancel.className="secondary";cancel.textContent="Cancel";cancel.disabled=busy;
  cancel.addEventListener("click",()=>cancelSchedule(item.id));
  row.append(text,dates,edit,cancel);container.append(row);
 }
}
async function cancelSchedule(id) {
 if(busy)return;busy=true;
 try{
  const data=await request(messageEndpoint+"/cancel",{id});
  if(editingId===id){editingId=null;setMode();}
  showSaved(data);feedback("Schedule cancelled.");
 }catch(error){feedback(error.message,true);}
 finally{busy=false;if(lastSaved)showSaved(lastSaved);}
}
async function request(path,payload) {
 const options=payload===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)};
 const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),10000);
 try {
  const response=await fetch(path,{...options,cache:"no-store",signal:controller.signal});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error||"Request failed.");
  $("connection").textContent="Connected at home"; $("connection").className="connection online";
  return data;
 } finally {clearTimeout(timer);}
}
async function refresh() {
 if(busy) return;
 try{showSaved(await request(messageEndpoint));}
 catch{$("connection").textContent="Connection unavailable";$("connection").className="connection";}
}
async function send(clear=false) {
 if(busy) return;
 busy=true;$("send").disabled=true;$("clear").disabled=true;feedback(clear?"Clearing…":"Saving your message…");
 try{
  const scheduled=!clear&&$("mode").value==="schedule";
  const payload=clear?{}:{text:normalized(),color:document.querySelector('input[name="color"]:checked').value,expires_minutes:Number($("expiry").value)};
  if(scheduled){payload.start=$("start").value;payload.end=$("end").value;if(editingId)payload.id=editingId;}
  const data=await request(clear?clearEndpoint:scheduled?messageEndpoint+"/schedule":messageEndpoint,payload);
  if(scheduled){editingId=null;setMode();}
  showSaved(data);
  feedback(clear?"Cleared. Future schedules are kept.":scheduled?"Scheduled! It will join rotation during the selected window.":"Saved! Your message will appear on the next display refresh.");
 }catch(error){feedback(error.name==="AbortError"?"The request timed out. Check Currently saved before trying again.":error.message||"Could not connect. Please try again.",true);}
 finally{busy=false;$("send").disabled=!valid(normalized());if(lastSaved)showSaved(lastSaved);}
}
$("composer").addEventListener("submit",event=>{event.preventDefault();if(valid(normalized()))send();});
$("clear").addEventListener("click",()=>send(true));
$("message").addEventListener("input",draft);
document.querySelectorAll('input[name="color"]').forEach(input=>input.addEventListener("change",draft));
document.querySelectorAll("[data-example]").forEach(button=>button.addEventListener("click",()=>{$("message").value=button.dataset.example;draft();$("message").focus();}));
$("mode").addEventListener("change",()=>{editingId=null;setMode();});
$("stop-edit").addEventListener("click",()=>{editingId=null;setMode();feedback("Editing stopped. The saved schedule is unchanged.");});
const nextHour=Math.ceil(Date.now()/3600000)*3600;
$("start").value=localInput(nextHour);$("end").value=localInput(nextHour+3600);
setMode();draft();refresh();setInterval(refresh,15000);
