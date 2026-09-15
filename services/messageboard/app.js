"use strict";
const $ = (id) => document.getElementById(id);
const palette = {white:"#ffffff",green:"#66ff66",yellow:"#ffdd66",pink:"#ff88bb"};
const flowerMode = location.pathname === "/flowers";
const messageEndpoint = flowerMode ? "/api/flowers" : "/api/message";
const clearEndpoint = flowerMode ? "/api/flowers/clear" : "/api/clear";
let previewTimer = null;
let busy = false;
let lastSaved = null;
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
 $("saved-info").textContent=data.active?(data.expires_at?"Expires "+new Date(data.expires_at*1000).toLocaleString([], {hour:"2-digit",minute:"2-digit",month:"short",day:"numeric"}):"Stays until you clear or replace it."):"Send a note whenever you’re ready.";
 $("clear").disabled=busy||!data.active;
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
  const data=await request(clear?clearEndpoint:messageEndpoint,clear?{}:{text:normalized(),color:document.querySelector('input[name="color"]:checked').value,expires_minutes:Number($("expiry").value)});
  showSaved(data);
  feedback(clear?"Cleared. The display will update on its next refresh.":"Saved! Your message will appear on the next display refresh.");
 }catch(error){feedback(error.name==="AbortError"?"The request timed out. Check Currently saved before trying again.":error.message||"Could not connect. Please try again.",true);}
 finally{busy=false;$("send").disabled=!valid(normalized());$("clear").disabled=!lastSaved?.active;}
}
$("composer").addEventListener("submit",event=>{event.preventDefault();if(valid(normalized()))send();});
$("clear").addEventListener("click",()=>send(true));
$("message").addEventListener("input",draft);
document.querySelectorAll('input[name="color"]').forEach(input=>input.addEventListener("change",draft));
document.querySelectorAll("[data-example]").forEach(button=>button.addEventListener("click",()=>{$("message").value=button.dataset.example;draft();$("message").focus();}));
draft();refresh();setInterval(refresh,15000);
