// Matches Anna Flowers' fixed border and Pixlet Marquee coordinates.
function flowerPixels(text, color, frame) {
 const pixels=[];
 const colors=["#ff88aa","#cc88ff","#ffbb88","#ff66aa"];
 const rows=["..ppp..",".ppppp.",".ppppp.","..ppp..","ppppppp","ppppppp",".pp.pp.","...g..."];
 function flower(x,y,tint,inverted=false) {
  (inverted?[...rows].reverse():rows).forEach((row,dy)=>{
   [...row].forEach((pixel,dx)=>{
    if(pixel!==".")pixels.push([x+dx,y+dy,pixel==="p"?tint:"#449944"]);
   });
  });
 }
 for(let i=0;i<8;i++){flower(i*8,0,colors[i%4]);flower(i*8,24,colors[(i+2)%4],true);}
 for(const y of [8,16]){flower(0,y,"#cc88ff");flower(57,y,"#ff88aa");}
 const width=boardWidth(text);
 let x=width<=46?23-Math.floor(width/2):frame<=width?-frame:width+46-frame;
 for(const char of text){
  const glyph=boardFont[char];
  if(glyph)for(const [gx,gy] of glyph.pixels){
   const px=x+gx;
   if(px>=0&&px<46&&gy>=0&&gy<8)pixels.push([9+px,12+gy,color]);
  }
  x+=glyph?.width||5;
 }
 return pixels;
}
function flowerPreview(text,color) {
 const canvas=document.createElement("canvas");
 canvas.width=64;canvas.height=32;canvas.className="pixel-preview";
 canvas.setAttribute("role","img");canvas.setAttribute("aria-label","Scrolling flower message: "+text);
 $("preview-pages").append(canvas);
 const ctx=canvas.getContext("2d"), width=boardWidth(text);
 const frames=width<=46?1:width+46;
 const delay=Math.min(60,Math.floor(14000/(width+46)));
 let frame=0;
 function paint(){
  ctx.fillStyle="#000";ctx.fillRect(0,0,64,32);
  for(const [x,y,tint] of flowerPixels(text,color,frame)){ctx.fillStyle=tint;ctx.fillRect(x,y,1,1);}
  frame=(frame+1)%frames;
 }
 paint();
 $("page-count").textContent=!text?"Write a message to preview it.":frames===1?"Fits inside the flowers · no scrolling needed.":"Continuous scrolling · "+(frames*delay/1000).toFixed(1)+" seconds per loop · no page breaks.";
 return frames===1?null:setInterval(paint,delay);
}
