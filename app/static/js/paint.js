const canvas = document.getElementById("paint-overlay");
const ctx = canvas.getContext("2d", { alpha: true });const colorPicker = document.getElementById("color-picker");
const sizeSlider = document.getElementById("size-slider");
const sizeValue = document.getElementById("size-value");


let state = {
  tool: "brush",
  size: 10,
  drawing: false,
  points: [],
  colors: {
    brush: "#ff0000",
    bucket: "#00ff00",
    eraser: "#ffffff"
  }
};

state.shape = {
    mode: 'rect',
    start: null,
    points: []
};

state.text = {
    color: '#000000',
    size: 1.2,
    thickness: 2,
    font: 'sans',
    align: 'left'
};

state.shape.fillEnabled = true;

function setupCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const w = +canvas.getAttribute("width");
  const h = +canvas.getAttribute("height");
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  ctx.scale(dpr, dpr);
}
setupCanvas();
window.addEventListener("resize", setupCanvas);

// Helper Functions
function getCanvasXY(e) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const sx = (canvas.width / dpr) / rect.width;
  const sy = (canvas.height / dpr) / rect.height;
  return [
    Math.round((e.clientX - rect.left) * sx),
    Math.round((e.clientY - rect.top) * sy)
  ];
}

function getActiveImgEl() {
  const activeBtn = document.querySelector(".layer-item.active .layer-name");
  if (!activeBtn) return null;
  const index = [...document.querySelectorAll(".layer-item .layer-name")].indexOf(activeBtn);
  return document.getElementById(`layer${index}`);
}

function reloadImage() {
  const imgEl = getActiveImgEl();
  if (!imgEl) return;
  
  const base = imgEl.src.split("?")[0];
  imgEl.addEventListener("load", function onload() {
    imgEl.removeEventListener("load", onload);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });
  imgEl.src = `${base}?t=${Date.now()}`;
}

function drawPreviewRect(a, b) {
  ctx.clearRect(0,0, canvas.width, canvas.height);
  const x0 = Math.min(a.x, b.x), y0 = Math.min(a.y, b.y);
  const w = Math.abs(b.x - a.x), h = Math.abs(b.y - a.y);
  ctx.save();
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.colors.brush;
  if (state.shape.fillEnabled) {
    ctx.fillStyle = state.colors.bucket;
    ctx.fillRect(x0, y0, w, h);
  }
  ctx.strokeRect(x0, y0, w, h);
  ctx.restore();
}

function drawPreviewEllipse(a, b) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
  const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2;
  ctx.save();
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  if (state.shape.fillEnabled) {
    ctx.fillStyle = state.colors.bucket;
    ctx.fill();
  }
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.colors.brush;
  ctx.stroke();
  ctx.restore();
}

function drawPreviewPolygon(points) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (points.length < 2) return;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
  ctx.closePath();
  if (state.shape.fillEnabled) {
    ctx.fillStyle = state.colors.bucket;
    ctx.fill();
  }
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.colors.brush;
  ctx.stroke();
  ctx.restore();
}

function drawPreviewLine(a, b) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.colors.brush;
  ctx.stroke();
  ctx.restore();
}

function cycleShapeMode() {
    const order = [ 'rect', 'ellipse', 'line', 'polygon'];
    const i = order.indexOf(state.shape.mode);
    state.shape.mode = order[(i+1) % order.length];
}

// Drawing
function setupStroke() {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.tool === "eraser" ? "#ffffff" : state.colors[state.tool];
}

function updateShapeUI() {
  const btn = document.querySelector('[data-tool="shapes"]');
  if (!btn) return;
  const mode = state.shape.mode;
  const fill = state.shape.fillEnabled ? "Fill ON" : "Fill OFF";
  btn.title = `Shapes: ${mode}  •  ${fill}\n(Click to select, click again to cycle)`;
  btn.textContent = state.shape.fillEnabled ? "⬛" : "⬜";
}


function drawSegment(a, b) {
  setupStroke();
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
  ctx.stroke();
}

//API Callss
async function sendShape(payload) {
    try {
        const res = await fetch("/api/v1/tools/shape", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            console.error("Shape failed:", await res.text());
            return;
        }
    } catch (err) {
        console.error("Shape fetch error:", err);
    }
    reloadImage();
}

async function sendText(payload) {
    try {
        const res = await fetch("/api/v1/tools/text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            console.error("Text failed:", await res.text());
            return;
        }
    } catch (err) {
        console.error("Text fetch error:", err);
    }
    reloadImage();
}


async function sendStroke() {
  if (!state.points.length) return;
  
  try {
    const res = await fetch("/api/v1/tools/stroke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: state.tool,
        color: state.colors[state.tool],
        size: Math.round(state.size),
        points: state.points
      })
    });
    
    if (!res.ok) {
      console.error("Stroke failed:", await res.text());
      return;
    }
  } catch (err) {
    console.error("Fetch error:", err);
  }
  
  state.points = [];
  reloadImage();
}

async function sendBucketFill(x, y) {
  try {
    const res = await fetch("/api/v1/tools/bucket_fill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        color: state.colors.bucket,
        start_point: [x, y]
      })
    });
    
    if (!res.ok) {
      console.error("Fill failed:", await res.text());
      return;
    }
  } catch (err) {
    console.error("Fill error:", err);
  }
  
  reloadImage();
}

// Tool selection
function setActiveTool(tool) {
  state.tool = tool;
  
  document.querySelectorAll("[data-tool]").forEach(btn => {
    const isActive = btn.dataset.tool === tool;
    btn.classList.toggle("active", isActive);

    if (isActive && (tool === "brush" || tool === "bucket")) {
      btn.style.backgroundColor = state.colors[tool];
      btn.style.opacity = "1";
    } else {
      btn.style.backgroundColor = "";
      btn.style.opacity = "";
    }
  });
  
  if ((tool === "brush" || tool === "bucket") && colorPicker) {
    colorPicker.value = state.colors[tool];
    colorPicker.click();
  }

  if (tool === "textbox" && colorPicker) {
    colorPicker.value = state.text.color;
    colorPicker.click();
  }


  if (tool === "shapes") {
    updateShapeUI();
  }
}

// Event Listeners 
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-tool]");
  if (!btn) return;

  const tool = btn.dataset.tool;
  if (tool === state.tool && tool === "shapes") {
      cycleShapeMode();
      updateShapeUI();
  } else {
      setActiveTool(tool);
  }
});

colorPicker?.addEventListener("input", () => {
  if (state.tool === "textbox") {
    state.text.color = colorPicker.value;

    document.querySelectorAll(`[data-tool="textbox"]`).forEach(btn => {
      btn.style.backgroundColor = colorPicker.value;
    });
  } else {
    state.colors[state.tool] = colorPicker.value;
    document.querySelectorAll(`[data-tool="${state.tool}"]`).forEach(btn => {
      btn.style.backgroundColor = colorPicker.value;
    });
  }
});


sizeSlider?.addEventListener("input", (e) => {
  state.size = Math.max(1, parseInt(e.target.value, 10) || 1);
  if (sizeValue) sizeValue.textContent = state.size;
});

const fillCheckbox = document.getElementById("shape-fill-enabled");
if (fillCheckbox) {
  fillCheckbox.checked = !!state.shape.fillEnabled;
  fillCheckbox.addEventListener("change", () => {
    state.shape.fillEnabled = fillCheckbox.checked;
    updateShapeUI();
  });
}

// TEXT CONTROLS
const textFontSel = document.getElementById("text-font");
const textSizeSlider = document.getElementById("text-size");
const textSizeVal = document.getElementById("text-size-value");
const textThickSlider = document.getElementById("text-thickness");
const textThickVal = document.getElementById("text-thickness-value");
const textAlignSel = document.getElementById("text-align");

if (textFontSel) {
  textFontSel.value = state.text.font;
  textFontSel.addEventListener("change", () => {
    state.text.font = textFontSel.value;
  });
}
if (textSizeSlider && textSizeVal) {
  textSizeSlider.value = state.text.size;
  textSizeVal.textContent = state.text.size;
  textSizeSlider.addEventListener("input", () => {
    state.text.size = parseFloat(textSizeSlider.value) || 1.0;
    textSizeVal.textContent = state.text.size.toFixed(1);
  });
}
if (textThickSlider && textThickVal) {
  textThickSlider.value = state.text.thickness;
  textThickVal.textContent = state.text.thickness;
  textThickSlider.addEventListener("input", () => {
    state.text.thickness = Math.max(1, parseInt(textThickSlider.value, 10) || 1);
    textThickVal.textContent = state.text.thickness;
  });
}
if (textAlignSel) {
  textAlignSel.value = state.text.align;
  textAlignSel.addEventListener("change", () => {
    state.text.align = textAlignSel.value;
  });
}


// Canvas Events 
canvas.addEventListener("pointerdown", async (e) => {
  e.preventDefault();
  
  if (state.tool === "bucket") {
    const [x, y] = getCanvasXY(e);
    await sendBucketFill(x, y);
    return;
  }

  if (state.tool === "textbox") {
      const [x, y] = getCanvasXY(e);
      const text = prompt("Enter text:");
      if (text && text.trim().length) {
          await sendText({
              text,
              origin: [x, y],
              color: state.text.color,
              size: state.text.size,
              thickness: state.text.thickness,
              font: state.text.font,
              align: state.text.align
          });
      }
      return;
  }

  if (state.tool === "shapes") {
      const [x, y] = getCanvasXY(e);
      if (state.shape.mode === "polygon") {
          state.shape.points.push({ x, y });
          drawPreviewPolygon(state.shape.points)
      } else {
          state.shape.start = { x, y };
          state.drawing = true;
          canvas.setPointerCapture(e.pointerId);
      }
      return;
  }

  if (state.tool === "brush" || state.tool === "eraser") {
    canvas.setPointerCapture(e.pointerId);
    state.drawing = true;
    state.points = [getCanvasXY(e)];
  }
});

canvas.addEventListener("pointermove", (e) => {
    if (state.tool === "shapes" && state.drawing && state.shape.start) {
        const [x, y] = getCanvasXY(e);
        const a = state.shape.start, b = { x, y };
        if (state.shape.mode === "rect") drawPreviewRect(a, b);
        if (state.shape.mode === "ellipse") drawPreviewEllipse(a, b);
        if (state.shape.mode === "line") drawPreviewLine(a, b);
        return;
    }

    if (!state.drawing) return;
  
      const p = getCanvasXY(e);
      const last = state.points[state.points.length - 1];
      drawSegment(last, p);
      state.points.push(p);
});

canvas.addEventListener("pointerup", async (e) => {
  if (state.tool === "shapes") {
    if (state.shape.mode === "polygon") {
      // Double-click to commit polygon
      if (e.detail === 2 && state.shape.points.length >= 3) {
        await sendShape({
          shape: "polygon",
          points: state.shape.points.map(p => [p.x, p.y]),
          fill: state.shape.fillEnabled ? state.colors.bucket : null,
          stroke: state.colors.brush,
          strokeWidth: state.size,
          fillAlpha: 255,
          strokeAlpha: 255
        });
        state.shape.points = [];
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    // rect / ellipse / line
    if (state.drawing && state.shape.start) {
      const [x, y] = getCanvasXY(e);
      const start = [state.shape.start.x, state.shape.start.y];
      const end   = [x, y];

      await sendShape({
        shape: state.shape.mode,
        start,
        end,
        fill: state.shape.fillEnabled ? state.colors.bucket : null,
        stroke: state.colors.brush,
        strokeWidth: state.size,
        fillAlpha: 255,
        strokeAlpha: 255
      });

      state.drawing = false;
      state.shape.start = null;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      try { canvas.releasePointerCapture(e.pointerId); } catch {}
    }
    return;
  }

  if (!state.drawing) return;

  state.drawing = false;
  state.points.push(getCanvasXY(e));
  await sendStroke();
});

canvas.addEventListener("pointercancel", () => {
  state.drawing = false;
  state.points = [];
  ctx.clearRect(0, 0, canvas.width, canvas.height);
});

canvas.addEventListener("dragstart", (e) => e.preventDefault());

// Initialize brush tool as active
setActiveTool("brush");
updateShapeUI();
