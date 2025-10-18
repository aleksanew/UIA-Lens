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

// Drawing
function setupStroke() {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = state.size;
  ctx.strokeStyle = state.tool === "eraser" ? "#ffffff" : state.colors[state.tool];
}

function drawSegment(a, b) {
  setupStroke();
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
  ctx.stroke();
}

//API Callss
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
}

// Event Listeners 
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-tool]");
  if (btn) setActiveTool(btn.dataset.tool);
});

colorPicker?.addEventListener("input", () => {
  state.colors[state.tool] = colorPicker.value;
  
  document.querySelectorAll(`[data-tool="${state.tool}"]`).forEach(btn => {
    btn.style.backgroundColor = colorPicker.value;
  });
});

sizeSlider?.addEventListener("input", (e) => {
  state.size = Math.max(1, parseInt(e.target.value, 10) || 1);
  if (sizeValue) sizeValue.textContent = state.size;
});

// Canvas Events 
canvas.addEventListener("pointerdown", async (e) => {
  e.preventDefault();
  
  if (state.tool === "bucket") {
    const [x, y] = getCanvasXY(e);
    await sendBucketFill(x, y);
    return;
  }
  
  if (state.tool === "brush" || state.tool === "eraser") {
    canvas.setPointerCapture(e.pointerId);
    state.drawing = true;
    state.points = [getCanvasXY(e)];
  }
});

canvas.addEventListener("pointermove", (e) => {
  if (!state.drawing) return;
  
  const p = getCanvasXY(e);
  const last = state.points[state.points.length - 1];
  drawSegment(last, p);
  state.points.push(p);
});

canvas.addEventListener("pointerup", async (e) => {
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