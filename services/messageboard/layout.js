// Keep wrapping and coordinates in sync with apps/messageboard/messageboard.star.
function boardWidth(text) {
 return [...text].reduce((width, char) => width + (boardFont[char]?.width || 5), 0);
}
function boardLines(text) {
 const lines = []; let line = "";
 for (const word of text.split(/\s+/u).filter(Boolean)) {
  const candidate = line + (line ? " " : "") + word;
  if (boardWidth(candidate) <= 60) { line = candidate; continue; }
  if (line) lines.push(line);
  line = "";
  for (const char of word) {
   if (boardWidth(line + char) > 60) { lines.push(line); line = ""; }
   line += char;
  }
 }
 if (line) lines.push(line);
 return lines;
}
function boardPixels(lines, page, total) {
 const pixels = [];
 lines.forEach((line, row) => {
  let x = 32 - Math.floor(boardWidth(line) / 2);
  for (const char of line) {
   const glyph = boardFont[char];
   if (glyph) for (const [gx, gy] of glyph.pixels) {
    if (gx >= 0 && gx < glyph.width && gy >= 0 && gy < 8)
     pixels.push([x + gx, 3 + row * 8 + gy, true]);
   }
   x += glyph?.width || 5;
  }
 });
 if (total > 1) for (let i=0;i<total;i++)
  for (let x=0;x<Math.floor(60/total);x++)
   pixels.push([2+i*Math.floor(60/total)+x,31,i===page]);
 return pixels;
}
