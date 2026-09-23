"use strict";
const $=id=>document.getElementById(id);
let busy=false, current=null;
function feedback(text,error=false){$("feedback").textContent=text;$("feedback").className=error?"error":"success";}
async function api(path,data){
 const response=await fetch(path,{cache:"no-store",...(data?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}:{})});
 const result=await response.json();
 if(!response.ok)throw new Error(result.error||"Request failed.");
 $("connection").textContent="Connected at home";return result;
}
function show(data){
 current=data;$("seconds").value=String(data.seconds);$("gallery").replaceChildren();
 if(!data.items.length){const p=document.createElement("p");p.textContent="Your folder is empty. Upload a GIF to start."; $("gallery").append(p);}
 data.items.forEach((item,index)=>{
  const row=document.createElement("section");row.className="schedule-item";
  const title=document.createElement("p");title.textContent=(index+1)+". "+item.name;
  const img=document.createElement("img");img.className="pixel-preview";img.width=64;img.height=32;
  img.alt=item.name+" — "+item.fit+" preview";img.src="/api/gifs/preview/"+item.id+"?seconds="+data.seconds;
  row.append(title,img);
  for(const [action,label] of [["up","Move up"],["down","Move down"],["remove","Remove"]]){
   const button=document.createElement("button");button.type="button";button.className="secondary";button.textContent=label;
   button.disabled=busy||(action==="up"&&index===0)||(action==="down"&&index===data.items.length-1);
   button.addEventListener("click",()=>mutate("/api/gifs/change",{action,id:item.id}));row.append(button);
  }
  $("gallery").append(row);
 });
}
async function mutate(path,data){
 if(busy)return;busy=true;$("upload").disabled=true;$("seconds").disabled=true;feedback("Saving…");
 try{show(await api(path,data));feedback("Saved. The display picks up changes on its next render.");}
 catch(error){feedback(error.message,true);}
 finally{busy=false;$("upload").disabled=false;$("seconds").disabled=false;if(current)show(current);}
}
$("upload-form").addEventListener("submit",async event=>{
 event.preventDefault();if(busy)return;
 const file=$("file").files[0];if(!file)return;
 if(file.size>8*1024*1024){feedback("Choose a GIF under 8 MB.",true);return;}
 const fit=$("fit").value;
 const reader=new FileReader();
 reader.onload=()=>mutate("/api/gifs/upload",{name:file.name,fit,data:reader.result.split(",")[1]});
 reader.onerror=()=>feedback("Could not read that file.",true);
 reader.readAsDataURL(file);
});
$("seconds").addEventListener("change",()=>mutate("/api/gifs/change",{action:"duration",seconds:Number($("seconds").value)}));
api("/api/gifs").then(show).catch(error=>{feedback(error.message,true);$("connection").textContent="Connection unavailable";});
