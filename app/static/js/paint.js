const canvas = document.getElementById("paint-overlay");
const ctx = canvas.getContext("2d", { alpha: true });
const colorPicker = document.getElementById("color-picker");
const sizeSlider = document.getElementById("size-slider");
const sizeValue = document.getElementById("size-value");
const brushTypeSelect = document.getElementById("brush-type-select");
const brushPopup = document.getElementById("brush-popup");
const eraserPopup = document.getElementById("eraser-popup");
const eraserSizeSlider = document.getElementById("eraser-size-slider");
const eraserSizeValue = document.getElementById("eraser-size-value");
const bucketColorPicker = document.getElementById("bucket-color-picker");


let state = {
  tool: "brush",
  brushSize: 10,
  eraserSize: 10,
  brushType: "hard",
  drawing: false,
  points: [],
  colors: {
    brush: "#ff0000",
    bucket: "#00ff00",
    eraser: "#ffffff",
  },
  currentStamp: null,
};

const BRUSH_SPACING = { default: 0.25, star: 3 };

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

// BRUSH TYPES AND STAMPS
function createSoftRoundStamp(size) {
  const stamp = [];
  const center = Math.floor(size / 2);
  const denom = 2 * (size / 4) ** 2;

  for (let y = 0; y < size; y++) {
    const row = (stamp[y] = []);
    for (let x = 0; x < size; x++) {
      const dx = x - center;
      const dy = y - center;
      row[x] = Math.exp(-(dx * dx + dy * dy) / denom);
    }
  }
  return stamp;
}

function createChalkStamp(size) {
  let stamp = createSoftRoundStamp(size);

  // Add fine-grained noise for chalk texture
  const noiseArray = [];
  for (let y = 0; y < size; y++) {
    const row = (noiseArray[y] = []);
    for (let x = 0; x < size; x++) row[x] = Math.random();
  }
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const noise = noiseArray[y][x] > 0.4 ? 1 : 0;
      stamp[y][x] = stamp[y][x] * (0.6 + noise * 0.4);
    }
  }

  // Add larger "holes" for chalk effect
  const largeNoiseArray = [];
  for (let y = 0; y < size; y++) {
    const row = (largeNoiseArray[y] = []);
    for (let x = 0; x < size; x++) row[x] = Math.random();
  }
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const hole = largeNoiseArray[y][x] > 0.85 ? 1 : 0;
      stamp[y][x] = stamp[y][x] * (1 - hole * 0.7);
    }
  }
  return stamp;
}


function gaussianBlurStamp(stamp, kernelSize, sigma) {
  const size = stamp.length;
  const half = Math.floor(kernelSize / 2);

  // Generate Gaussian kernel 
  const kernel = [];
  let kernelSum = 0;
  for (let y = -half; y <= half; y++) {
    const row = (kernel[y + half] = []);
    for (let x = -half; x <= half; x++) {
      const v = Math.exp(-(x * x + y * y) / (2 * sigma * sigma));
      row[x + half] = v;
      kernelSum += v;
    }
  }
  // Normalize kernel
  for (let y = 0; y < kernelSize; y++) {
    for (let x = 0; x < kernelSize; x++) kernel[y][x] /= kernelSum;
  }

  // Convolve stamp with kernel
  const out = Array(size)
    .fill(0)
    .map(() => Array(size).fill(0));
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let sum = 0;
      for (let ky = -half; ky <= half; ky++) {
        for (let kx = -half; kx <= half; kx++) {
          const ny = y + ky;
          const nx = x + kx;
          if (ny >= 0 && ny < size && nx >= 0 && nx < size) {
            sum += stamp[ny][nx] * kernel[ky + half][kx + half];
          }
        }
      }
      out[y][x] = sum;
    }
  }
  return out;
}

function createWatercolorStamp(size) {
  const stamp = Array(size).fill(0).map(() => Array(size).fill(0));
  const center = Math.floor(size / 2);
  const radiusFactors = [0.5, 0.7, 0.9, 1.1];

  // Create multiple layers for watercolor effect
  for (const rf of radiusFactors) {
    const layer = Array(size).fill(0).map(() => Array(size).fill(0));
    // Generate noise for organic deformation
    const noise = [];
    for (let y = 0; y < size; y++) {
      const row = (noise[y] = []);
      for (let x = 0; x < size; x++) row[x] = Math.random() * 0.3;
    }

    // Create layer for radial gradient with noise
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const dx = x - center;
        const dy = y - center;
        const dist = Math.hypot(dx, dy);
        const target = (size / 2) * rf;
        let v = Math.max(0, 1 - dist / target);
        v *= 0.8 + noise[y][x];
        layer[y][x] = v;
      }
    }

    // Combine layer into stamp using max blending
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        stamp[y][x] = Math.max(stamp[y][x], layer[y][x] * (1.0 / rf));
      }
    }
  }

  // Apply Gaussian blur for soft edges
  const blurred = gaussianBlurStamp(stamp, 7, 2);
  return blurred;
}

function fillPolygon(stamp, points, value) {
  const size = stamp.length;
  let minY = size,
    maxY = 0;

  // Find Y bounds
  for (const [, y] of points) {
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }

  // Scanline fill
  for (let y = minY; y <= maxY && y < size; y++) {
    const xs = [];

    // Find intersections with polygon edges
    for (let i = 0; i < points.length; i++) {
      const [x1, y1] = points[i];
      const [x2, y2] = points[(i + 1) % points.length];
      if ((y1 <= y && y < y2) || (y2 <= y && y < y1)) {
        const x = x1 + ((y - y1) * (x2 - x1)) / (y2 - y1);
        xs.push(Math.round(x));
      }
    }
    // Fill between pairs of intersections
    xs.sort((a, b) => a - b);
    for (let i = 0; i < xs.length - 1; i += 2) {
      const xStart = Math.max(0, xs[i]);
      const xEnd = Math.min(size - 1, xs[i + 1]);
      for (let x = xStart; x <= xEnd; x++) if (y >= 0 && y < size) stamp[y][x] = value;
    }
  }
}

function createStarStamp(size) {
  const stamp = Array(size).fill(0).map(() => Array(size).fill(0));
  const c = Math.floor(size / 2);
  const outer = Math.floor(size / 2);
  const inner = Math.floor(outer / 2.5);

  // Generate star points
  const points = [];
  for (let i = 0; i < 10; i++) {
    const angle = i * (Math.PI / 5) - Math.PI / 2; // start at top
    const r = i % 2 === 0 ? outer : inner;
    const x = Math.round(c + r * Math.cos(angle));
    const y = Math.round(c + r * Math.sin(angle));
    points.push([x, y]);
  }
  fillPolygon(stamp, points, 1.0);
  return stamp;
}

// UTILS 
function hexToRgb(hex) {
  hex = hex.replace("#", "");
  if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
  return {
    r: parseInt(hex.substring(0, 2), 16),
    g: parseInt(hex.substring(2, 4), 16),
    b: parseInt(hex.substring(4, 6), 16),
  };
}

function stampToCanvas(stamp, color) {
  const size = stamp.length;
  const stampCanvas = document.createElement("canvas");
  stampCanvas.width = size;
  stampCanvas.height = size;
  const stampCtx = stampCanvas.getContext("2d");

  const imageData = stampCtx.createImageData(size, size);
  const data = imageData.data;
  const rgb = hexToRgb(color);

  // Set RGBA vaules for each pixel
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const v = Math.max(0, Math.min(1, stamp[y][x]));
      const i = (y * size + x) * 4;
      data[i + 0] = rgb.r;
      data[i + 1] = rgb.g;
      data[i + 2] = rgb.b;
      data[i + 3] = Math.round(v * 255); // Alpha from stamp value
    }
  }
  stampCtx.putImageData(imageData, 0, 0);
  return stampCanvas;
}

// Manual alpha blending of stamp onto canvas
function applyStamp(stampBundle, x, y) {
  const dpr = window.devicePixelRatio || 1;

  const cssStamp = stampBundle.css;
  const devStamp = stampBundle.dev;

  const sizeCSS = cssStamp.width;
  const halfCSS = Math.floor(sizeCSS / 2);


  const canvasWidthCSS = canvas.width / dpr;
  const canvasHeightCSS = canvas.height / dpr;

  // Calculate bounds in CSS coordinates
  const x1CSS = Math.max(0, x - halfCSS);
  const y1CSS = Math.max(0, y - halfCSS);
  const x2CSS = Math.min(canvasWidthCSS, x + halfCSS);
  const y2CSS = Math.min(canvasHeightCSS, y + halfCSS);

  if (x2CSS <= x1CSS || y2CSS <= y1CSS) return;

  const wCSS = Math.round(x2CSS - x1CSS);
  const hCSS = Math.round(y2CSS - y1CSS);


  const dx = Math.round(x1CSS * dpr);
  const dy = Math.round(y1CSS * dpr);
  const dw = Math.max(1, Math.round(wCSS * dpr));
  const dh = Math.max(1, Math.round(hCSS * dpr));

  const sx1CSS = halfCSS - (x - x1CSS);
  const sy1CSS = halfCSS - (y - y1CSS);
  const sx1DEV = Math.max(0, Math.round(sx1CSS * dpr));
  const sy1DEV = Math.max(0, Math.round(sy1CSS * dpr));

  const existingData = ctx.getImageData(dx, dy, dw, dh);
  const existing = existingData.data;

  const stampCtxDEV = devStamp.getContext("2d");
  const stampData = stampCtxDEV.getImageData(sx1DEV, sy1DEV, dw, dh);
  const stamp = stampData.data;

  for (let i = 0; i < existing.length; i += 4) {
    const sr = stamp[i + 0];
    const sg = stamp[i + 1];
    const sb = stamp[i + 2];
    const sa = stamp[i + 3] / 255;

    if (sa <= 0) continue;

    const dr = existing[i + 0];
    const dg = existing[i + 1];
    const db = existing[i + 2];
    const da = existing[i + 3];

    existing[i + 0] = Math.round(dr * (1 - sa) + sr * sa);
    existing[i + 1] = Math.round(dg * (1 - sa) + sg * sa);
    existing[i + 2] = Math.round(db * (1 - sa) + sb * sa);

    existing[i + 3] = Math.max(da, Math.round(sa * 255));
  }


  ctx.putImageData(existingData, dx, dy);
}


function getCanvasXY(e) {
  const rect = canvas.getBoundingClientRect();

  const clientX = e.clientX - rect.left;
  const clientY = e.clientY - rect.top;

  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.width / dpr;
  const cssHeight = canvas.height / dpr;

  // Convert from 
  const scaleX = cssWidth / rect.width;
  const scaleY = cssHeight / rect.height;

  const x = Math.round(clientX * scaleX);
  const y = Math.round(clientY * scaleY);

  return [x, y];
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


const STAMP_FACTORIES = {
  chalk: createChalkStamp,
  watercolor: createWatercolorStamp,
  star: createStarStamp,
  soft: createSoftRoundStamp,
};

function getCachedStamp(brushType, size, color) {
  const dpr = window.devicePixelRatio || 1;
  const key = `${brushType}-${size}-${color}-dpr${dpr}`;
  if (state.currentStamp?.key === key) return state.currentStamp;

  const factory = STAMP_FACTORIES[brushType] ?? STAMP_FACTORIES.soft;
  const stamp = factory(size);

  const cssCanvas = stampToCanvas(stamp, color);

  const devCanvas = document.createElement("canvas");
  devCanvas.width = Math.max(1, Math.round(cssCanvas.width * dpr));
  devCanvas.height = Math.max(1, Math.round(cssCanvas.height * dpr));
  const dctx = devCanvas.getContext("2d");
  dctx.drawImage(cssCanvas, 0, 0, devCanvas.width, devCanvas.height);

  const spacing = BRUSH_SPACING[brushType] ?? BRUSH_SPACING.default;
  return (state.currentStamp = { key, css: cssCanvas, dev: devCanvas, spacing });
}

function drawSegment(a, b) {
  const size = state.tool === "eraser" ? state.eraserSize : state.brushSize;
  const color = state.tool === "eraser" ? "#ffffff" : state.colors[state.tool];

  if (state.brushType === "hard" || state.tool === "eraser") {
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = size;
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = state.tool === "eraser" ? state.colors.eraser || "#ffffff" : color;
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
    ctx.restore();
    return;
  }

  const stampBundle = getCachedStamp(state.brushType, size, color);
  const [x1, y1] = a;
  const [x2, y2] = b;

  const distance = Math.hypot(x2 - x1, y2 - y1);
  const steps = Math.max(1, Math.floor(distance / (size * stampBundle.spacing)));

  for (let s = 0; s <= steps; s++) {
    const t = s / Math.max(1, steps);
    const x = Math.round(x1 + (x2 - x1) * t);
    const y = Math.round(y1 + (y2 - y1) * t);
    applyStamp(stampBundle, x, y);
  }
}


async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : null;
}

async function sendStroke() {
  if (!state.points.length) return;
  const size = state.tool === "eraser" ? state.eraserSize : state.brushSize;

  try {
    await postJSON("/api/v1/tools/stroke", {
      tool: state.tool,
      color: state.colors[state.tool],
      size: Math.round(size),
      points: state.points,
      brush_type: state.brushType,
    });
  } catch (e) {
    console.error("Stroke failed:", e.message);
  }
  state.points = [];
  reloadImage();
}

async function sendBucketFill(x, y) {
  try {
    await postJSON("/api/v1/tools/bucket_fill", {
      color: state.colors.bucket,
      start_point: [x, y],
    });
  } catch (e) {
    console.error("Fill failed:", e.message);
  }
  reloadImage();
}

async function sendPickColor(x, y) {
  try {
    const data = await postJSON("/api/v1/tools/dropper", { x, y });
    const hex = data?.hex;
    if (!hex) return;
    setToolColor("brush", hex);
    setActiveTool("brush");
  } catch (e) {
    console.error("Dropper failed:", e.message);
  }
}


// tool selection and UI
function setToolColor(tool, hex) {
  state.colors[tool] = hex;
  document.querySelectorAll(`[data-tool="${tool}"]`).forEach((btn) => {
    btn.style.backgroundColor = hex;
    btn.style.opacity = "1";
  });
  if ((tool === "brush" || tool === "bucket") && colorPicker) {
    colorPicker.value = hex;
  }
  if (tool === "brush") state.currentStamp = null;
}

function setActiveTool(tool) {
  state.tool = tool;

  document.querySelectorAll("[data-tool]").forEach((btn) => {
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

  showOnlyPopup(null);

  if ((tool === "brush" || tool === "bucket") && colorPicker) {
    colorPicker.value = state.colors[tool];
  }
}

function showOnlyPopup(which) {
  brushPopup?.classList.toggle("show", which === "brush");
  eraserPopup?.classList.toggle("show", which === "eraser");
}


// event listeners
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-tool]");

  if (!btn) {
    if (!e.target.closest('[data-tool="brush"]') && !brushPopup?.contains(e.target)) {
      brushPopup?.classList.remove("show");
    }
    if (!e.target.closest('[data-tool="eraser"]') && !eraserPopup?.contains(e.target)) {
      eraserPopup?.classList.remove("show");
    }
    return;
  }

  const tool = btn.dataset.tool;

  if (tool === "brush") {
    if (state.tool === "brush") {
      brushPopup?.classList.toggle("show");
      eraserPopup?.classList.remove("show");
    } else {
      setActiveTool("brush");
      showOnlyPopup("brush");
    }
    return;
  }

  if (tool === "eraser") {
    if (state.tool === "eraser") {
      eraserPopup?.classList.toggle("show");
      brushPopup?.classList.remove("show");
    } else {
      setActiveTool("eraser");
      showOnlyPopup("eraser");
    }
    return;
  }

  if (tool === "bucket") {
    setActiveTool("bucket");
    bucketColorPicker?.click();
    return;
  }

  setActiveTool(tool);
});

colorPicker?.addEventListener("input", () => {
  setToolColor(state.tool, colorPicker.value);
});

bucketColorPicker?.addEventListener("input", () => {
  setToolColor("bucket", bucketColorPicker.value);
});

sizeSlider?.addEventListener("input", (e) => {
  state.brushSize = Math.max(1, parseInt(e.target.value, 10) || 1);
  if (sizeValue) sizeValue.textContent = state.brushSize;
  state.currentStamp = null;
});

eraserSizeSlider?.addEventListener("input", (e) => {
  state.eraserSize = Math.max(1, parseInt(e.target.value, 10) || 1);
  if (eraserSizeValue) eraserSizeValue.textContent = state.eraserSize;
});

brushTypeSelect?.addEventListener("change", (e) => {
  state.brushType = e.target.value;
  state.currentStamp = null;
});


canvas.addEventListener(
  "pointerdown",
  async (e) => {
    e.preventDefault();

    if (state.tool === "bucket") {
      const [x, y] = getCanvasXY(e);
      await sendBucketFill(x, y);
      return;
    }
    if (state.tool === "dropper") {
      const [x, y] = getCanvasXY(e);
      await sendPickColor(x, y);
      return;
    }

    if (state.tool === "brush" || state.tool === "eraser") {
      canvas.setPointerCapture(e.pointerId);
      state.drawing = true;
      state.points = [getCanvasXY(e)];
    }
  },
  { passive: false }
);

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


setActiveTool("brush");
