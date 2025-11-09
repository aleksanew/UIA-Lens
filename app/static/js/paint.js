const canvas = document.getElementById("paint-overlay");
const ctx = canvas.getContext("2d", { alpha: true });const colorPicker = document.getElementById("color-picker");
const sizeSlider = document.getElementById("size-slider");
const sizeValue = document.getElementById("size-value");
const bucketColorPicker = document.getElementById("bucket-color-picker");
const brushPopup        = document.getElementById("brush-popup");
const eraserPopup       = document.getElementById("eraser-popup");
const eraserSizeSlider  = document.getElementById("eraser-size-slider");
const eraserSizeValue   = document.getElementById("eraser-size-value");
const brushTypeSelect   = document.getElementById("brush-type-select");


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
const BRUSH_SPACING = { default: 0.25, star: 3 };
const currentSize = () => (state.tool === "eraser" ? state.eraserSize : state.brushSize);

state.selection = {
  active: false,      // Whether an active selection exists
  type: null,         // 'rect', 'freeform', 'polygonal', 'magnetic'
  coords: null,       // For rect selection: [x1, y1, x2, y2]
  path: null,         // For freeform [[x1,y1], [x2,y2], ...] makes it easier to not combine these two i think
  vertices: null,     // For polygonal [[x1,y1], [x2,y2], ...]
  raw_clicks: null,   // For magnetic lasso: [[x1,y1], [x2,y2], ...] raw user clicks before server processing
  mask: null,         // Base64 mask from server (optional)
  preview: {
    start: null,      // Starting point for rect selection
    current: null,    // Current mouse position
    points: []        // For polygonal/freeform
  },
  transform: {
    dx: 0,            // Offset from original position
    dy: 0,
    scaleX: 1.0,
    scaleY: 1.0
  },
  isDragging: false,
  dragStart: null,
  isPasted: false,
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

function drawPreviewRect(a, b) {
  ctx.clearRect(0,0, canvas.width, canvas.height);
  const x0 = Math.min(a.x, b.x), y0 = Math.min(a.y, b.y);
  const w = Math.abs(b.x - a.x), h = Math.abs(b.y - a.y);
  ctx.save();
  ctx.lineWidth = currentSize();
  ctx.strokeStyle = state.colors.brush;
  if (state.shape.fillEnabled) {
    ctx.fillStyle = state.colors.bucket;
    ctx.fillRect(x0, y0, w, h);
  }
  ctx.strokeRect(x0, y0, w, h);
  ctx.restore();
}

// Point-in-polygon test using ray casting algorithm
function isPointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];
    
    const intersect = ((yi > y) !== (yj > y))
        && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
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
  ctx.lineWidth = currentSize();
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
  ctx.lineWidth = currentSize();
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
  ctx.lineWidth = currentSize();
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
  ctx.lineWidth = currentSize();
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

function drawSelectionPreview() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (state.tool === "select_rect" && state.selection.active && state.selection.coords) {
    // Draw the selection rectangle with transform applied
    const [x1, y1, x2, y2] = state.selection.coords;
    const dx = state.selection.transform.dx;
    const dy = state.selection.transform.dy;
    
    const x = x1 + dx;
    const y = y1 + dy;
    const w = x2 - x1;
    const h = y2 - y1;
    
    ctx.save();
    ctx.strokeStyle = "#00aaff";  // Blue selection outline
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);      // Dashed line
    ctx.strokeRect(x, y, w, h);
    
    // Draw corner handles for visual feedback
    const handleSize = 6;
    ctx.fillStyle = "#00aaff";
    ctx.fillRect(x - handleSize/2, y - handleSize/2, handleSize, handleSize);
    ctx.fillRect(x + w - handleSize/2, y - handleSize/2, handleSize, handleSize);
    ctx.fillRect(x - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
    ctx.fillRect(x + w - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
    
    ctx.restore();
  }
  
  // Also handle preview while drawing (before committed)
  if (state.tool === "select_rect" && state.selection.preview.start && state.selection.preview.current) {
    const start = state.selection.preview.start;
    const current = state.selection.preview.current;

    const x = Math.min(start.x, current.x);
    const y = Math.min(start.y, current.y);
    const w = Math.abs(current.x - start.x);
    const h = Math.abs(current.y - start.y);

    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(x, y, w, h);
    ctx.restore();
  }

  // Draw when active
  if (state.tool === "select_freeform" && state.selection.active && state.selection.path) {
    const dx = state.selection.transform.dx;
    const dy = state.selection.transform.dy;

    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    ctx.beginPath();
    const firstPt = state.selection.path[0];
    ctx.moveTo(firstPt[0] + dx, firstPt[1] + dy);

    for (let i = 1; i < state.selection.path.length; i++) {
      const pt = state.selection.path[i];
      ctx.lineTo(pt[0] + dx, pt[1] + dy);
    }

    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }

  // Preview when drawing freeform
  if (state.tool === "select_freeform" && state.selection.preview.points.length > 0) {
    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    ctx.beginPath();
    const pts = state.selection.preview.points;
    ctx.moveTo(pts[0].x, pts[0].y);

    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i].x, pts[i].y);
    }

    ctx.stroke();
    ctx.restore();
  }

  // Draw when active (polygonal)
  if (state.tool === "select_polygonal" && state.selection.active && state.selection.vertices) {
    const dx = state.selection.transform.dx;
    const dy = state.selection.transform.dy;

    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    const verts = state.selection.vertices;
    if (verts.length >= 2) {
      ctx.beginPath();
      ctx.moveTo(verts[0][0] + dx, verts[0][1] + dy);
      for (let i = 1; i < verts.length; i++) {
        ctx.lineTo(verts[i][0] + dx, verts[i][1] + dy);
      }
      ctx.closePath();
      ctx.stroke();
    }
    ctx.restore();
  }

  // Draw finalized magnetic selection even if current active tool is still 'select_magnetic'
  if (state.selection.type === "magnetic" && state.selection.active && state.selection.vertices && state.tool !== "select_polygonal") {
    const dx = state.selection.transform.dx;
    const dy = state.selection.transform.dy;

    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    const verts = state.selection.vertices;
    if (verts.length >= 2) {
      ctx.beginPath();
      ctx.moveTo(verts[0][0] + dx, verts[0][1] + dy);
      for (let i = 1; i < verts.length; i++) {
        ctx.lineTo(verts[i][0] + dx, verts[i][1] + dy);
      }
      ctx.closePath();
      ctx.stroke();
    }
    ctx.restore();
  }

  // Preview when drawing polygonal (only while collecting vertices)
  if (state.tool === "select_polygonal" && state.drawing && state.selection.preview.points.length > 0) {
    const pts = state.selection.preview.points;
    ctx.save();
    ctx.strokeStyle = "#00aaff";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i].x, pts[i].y);
    }
    // rubber-band to cursor if present
    if (state.selection.preview.current) {
      ctx.lineTo(state.selection.preview.current.x, state.selection.preview.current.y);
    }
    ctx.stroke();
    ctx.restore();
  }

  // preview for magnetic
  if (state.tool === "select_magnetic" && state.selection.preview.points.length > 0) {
    const pts = state.selection.preview.points;
    ctx.save();

    // distinct line to highlight its not the final form
    ctx.strokeStyle = "#ffaa00";
    ctx.lineWidth = 2;
    ctx.setLineDash([6,4]);
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.stroke();

    ctx.fillStyle = "#ffaa00";
    for (const pt of pts) {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }
}

function clearSelection() {
  state.selection.active = false;
  state.selection.coords = null;
  state.selection.path = null;
  state.selection.vertices = null;
  state.selection.mask = null;

  state.selection.isPasted = false;
  state.selection.pasteFromCut = false;
  state.selection.isCut = false;
 
  state.selection.transform = { dx: 0, dy: 0, scaleX: 1.0, scaleY: 1.0 };
  state.selection.preview = { start: null, current: null, points: [] };
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function buildSelectionPayload(sel) {
  const payload = { type: sel.type };
  switch (sel.type) {
    case "rect":
      payload.coords = sel.coords;
      break;
    case "freeform":
      payload.path = sel.path;
      break;
    case "polygonal":
      payload.vertices = sel.vertices;
      break;
    case "magic-lasso":
      payload.seed_points = sel.seed_points;
      break;
    case "magnetic":
      // Prefer sending finalized vertices if available; otherwise send raw_clicks
      if (sel.vertices && sel.vertices.length) payload.vertices = sel.vertices;
      else if (sel.raw_clicks && sel.raw_clicks.length) payload.raw_clicks = sel.raw_clicks;
      break;
  }
  return payload;
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

async function fetchSelectionMask() {
  if (!state.selection.active) return;

  const payload = { image_id: "current", ...buildSelectionPayload(state.selection) };

  try {
    const res = await fetch(`/api/v1/select/${state.selection.type}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      console.error("Selection fetch failed:", await res.text());
      return;
    }

    const data = await res.json();
    state.selection.mask = data.mask; // base64 mask

  } catch (err) {
    console.error("Selection fetch error:", err);
  }
}

async function finalizeMagneticSelection() {
  if (!state.selection.raw_clicks || state.selection.raw_clicks.length < 3) return;

  // make consitent with backend
  const payload = {
    image_id: "current",
    raw_clicks: state.selection.raw_clicks,
  };

  try {
    // POST using helper
    const res = await postJSON("/api/v1/select/magnetic", payload);
    if (!res) throw new Error("Empty response from magnetic finalize");

    // Server should return { path: [[x,y],...], mask: <base64>, segment_modes?: [...] }
    state.selection.vertices = res.path || [];
    state.selection.mask = res.mask || null;

  // Keep selection type as 'magnetic' so the UI/tool doesn't change unexpectedly.
  // Server now accepts 'magnetic' in apply/delete, so we don't force a tool switch here.
  state.selection.type = "magnetic";
    state.selection.active = true;
    state.drawing = false;
    state.selection.raw_clicks = null;
    state.selection.preview.points = [];

    // render the beauty
    drawSelectionPreview();
  } catch (err) {
    console.error("Magnetic finalize error:", err);
  }
}


async function copySelection() {
  if (!state.selection.active) return;

  state.selection.copied = true;
  state.selection.isCut = false;

  // Store original for pasting
  state.selection.clipboard = {
    mode: "copy",
    type: state.selection.type,
    coords: state.selection.coords ? [...state.selection.coords] : null,
    path: state.selection.path ? state.selection.path.map(pt => [...pt]) : null,
    vertices: state.selection.vertices ? state.selection.vertices.map(pt => [...pt]) : null,
  };
}

async function cutSelection() {
  if (!state.selection.active) return;

  state.selection.copied = true;
  state.selection.isCut = true;
  state.selection.clipboard = {
    mode: "cut",
    type: state.selection.type,
    coords: state.selection.coords ? [...state.selection.coords] : null,
    path: state.selection.path ? state.selection.path.map(pt => [...pt]) : null,
    vertices: state.selection.vertices ? state.selection.vertices.map(pt => [...pt]) : null,
  };

  // Visual feedback that its cut so dim area or those fancy edges stuff like that
}

async function pasteSelection() {
  if (!state.selection.copied || !state.selection.clipboard) return;

  const clip = state.selection.clipboard;

  // For now, just restore at original position might add restore on mouse pointer
  state.selection.coords = clip.coords ? [...clip.coords] : null;
  state.selection.path = clip.path ? clip.path.map(pt => [...pt]) : null;
  state.selection.vertices = clip.vertices ? clip.vertices.map(pt => [...pt]) : null;
  state.selection.type = clip.type;

  state.selection.active = true;
  state.selection.transform = { dx: 0, dy: 0, scaleX: 1.0, scaleY: 1.0 };
  state.selection.isPasted = true;
  state.selection.pasteFromCut = (clip.mode === "cut");

  drawSelectionPreview();

  // commit on user enter or click off
}

async function commitSelection() {
  if (!state.selection.active) return;
  
  let operation;

  // Prioritize pasted instances as copy, so dragging a pasted selection doesn't cut the original
  if (state.selection.isPasted) {
    operation = state.selection.pasteFromCut ? "move" : "copy";
  } else if (state.selection.isCut) {
    operation = "move";
  } else if (state.selection.transform.dx !== 0 ||
    state.selection.transform.dy !== 0 ||
    state.selection.transform.scaleX !== 1.0 ||
    state.selection.transform.scaleY !== 1.0) { 
    operation = "move";
  } else {
    clearSelection();
    return; // No operation to commit
  }

  const selectionData = buildSelectionPayload(state.selection);
  
  try {
    const res = await fetch("/api/v1/select/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operation,
        selection: selectionData,
        transform: state.selection.transform,
      })
    });
    
    if (!res.ok) {
      console.error("Commit failed:", await res.text());
      return;
    }

    reloadImage();
    clearSelection();
  } catch (err) {
    console.error("Commit error:", err);
  }
}

async function deleteSelection() {
  if (!state.selection.active) return;

  const selectionData = buildSelectionPayload(state.selection);

  try {
    const res = await fetch("/api/v1/select/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selection: selectionData,
      })
    });
    if (!res.ok) {
      console.error("Delete failed:", await res.text());
      return;
    }

    reloadImage();
    clearSelection();

  } catch (err) {
    console.error("Delete error:", err);
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

  if (tool === "textbox" && colorPicker) {
    colorPicker.value = state.text.color;
    colorPicker.click();
  }


  if (tool === "shapes") {
    updateShapeUI();
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
    // clicks outside: hide popups
    if (!e.target.closest('[data-tool="brush"]') && !brushPopup?.contains?.(e.target)) {
      brushPopup?.classList.remove("show");
    }
    if (!e.target.closest('[data-tool="eraser"]') && !eraserPopup?.contains?.(e.target)) {
      eraserPopup?.classList.remove("show");
    }
    return;
  }

  const tool = btn.dataset.tool;

  if (tool === "shapes") {
    if (state.tool === "shapes") {
      cycleShapeMode();
      updateShapeUI();
    } else {
      setActiveTool("shapes");
    }
    return;
  }

  if (tool === "brush") {
    if (state.tool === "brush") {
      brushPopup?.classList.toggle("show");
      eraserPopup?.classList.remove("show");
    } else {
      setActiveTool("brush");
      brushPopup?.classList.add("show");
      eraserPopup?.classList.remove("show");
    }
    return;
  }

  if (tool === "eraser") {
    if (state.tool === "eraser") {
      eraserPopup?.classList.toggle("show");
      brushPopup?.classList.remove("show");
    } else {
      setActiveTool("eraser");
      eraserPopup?.classList.add("show");
      brushPopup?.classList.remove("show");
    }
    return;
  }

  if (tool === "bucket") {
    setActiveTool("bucket");
    bucketColorPicker?.click?.();
    return;
  }

  if (tool === "select_rect") {
    setActiveTool("select_rect");
    state.selection.type = "rect";
    return;
  }

  if (tool === "select_freeform") {
    setActiveTool("select_freeform");
    state.selection.type = "freeform";
    return;
  }

  if (tool === "select_polygonal") {
    setActiveTool("select_polygonal");
    state.selection.type = "polygonal";
    return;
  }

  if (tool === "select_magnetic") {
    setActiveTool("select_magnetic");
    state.selection.type = "magnetic";
    // Ensure preview storage empty
    state.selection.raw_clicks = [];
    state.selection.preview.points = [];
    return;
  }

  // default tools (textbox, dropper, etc.)
  setActiveTool(tool);
});


colorPicker?.addEventListener("input", () => {
  if (state.tool === "textbox") {
    state.text.color = colorPicker.value;
    document.querySelectorAll(`[data-tool="textbox"]`).forEach(btn => {
      btn.style.backgroundColor = colorPicker.value;
    });
  } else if (state.tool === "brush" || state.tool === "bucket") {
    setToolColor(state.tool, colorPicker.value);
  }
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
  if (state.tool === "dropper") {
    const [x, y] = getCanvasXY(e);
    await sendPickColor(x, y);
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

  // Check if clicking inside an active selection to drag it
  if (state.selection.active) {
    const [mouseX, mouseY] = getCanvasXY(e);
    const dx = state.selection.transform.dx;
    const dy = state.selection.transform.dy;
    
    let insideSelection = false;

    if (state.selection.coords) {
      // Rectangular selection bounds check
      const [x1, y1, x2, y2] = state.selection.coords;
      insideSelection = (mouseX >= x1 + dx && mouseX <= x2 + dx && mouseY >= y1 + dy && mouseY <= y2 + dy);
    } else if (state.selection.path) {
      // Freeform selection - check if point is inside path using point-in-polygon
      const adjustedPath = state.selection.path.map(([x, y]) => [x + dx, y + dy]);
      insideSelection = isPointInPolygon(mouseX, mouseY, adjustedPath);
    } else if (state.selection.vertices) {
      // Polygonal selection - point-in-polygon using vertices
      const adjustedVerts = state.selection.vertices.map(([x, y]) => [x + dx, y + dy]);
      insideSelection = isPointInPolygon(mouseX, mouseY, adjustedVerts);
    }

    if (insideSelection) {
      state.selection.isDragging = true;
      state.selection.dragStart = { x: mouseX, y: mouseY };
      state.selection.initialTransform = { ...state.selection.transform };
      canvas.setPointerCapture(e.pointerId);
      return;
    }
  }

  if (state.tool === "select_magnetic") {

  // collect raw clicks for magnetic selection preview
  const [x, y] = getCanvasXY(e);
  state.selection.raw_clicks = state.selection.raw_clicks || [];
  state.selection.raw_clicks.push([x, y]);

  // Use preview.points as existing preview drawing code expects {x,y}
  state.selection.preview.points = state.selection.raw_clicks.map(([px, py]) => ({ x: px, y: py }));

  // Ensure drawing mode
  state.drawing = true;
  drawSelectionPreview(); // reuse the existing preview draw
  return;
}

  if (state.tool === "select_rect") {
    // Clear previous selection
    clearSelection();

    const [x, y] = getCanvasXY(e);
    state.selection.preview.start = { x, y };
    state.drawing = true;
    canvas.setPointerCapture(e.pointerId);
    return;
  }

  if (state.tool === "select_freeform") {
    clearSelection();

    const [x, y] = getCanvasXY(e);
    state.selection.preview.points = [{ x,y}];
    state.drawing = true;
    canvas.setPointerCapture(e.pointerId);
    return;
  }

  if (state.tool === "select_polygonal") {
    // Start or extend polygon
    const [x, y] = getCanvasXY(e);
    if (!state.selection.active && state.selection.preview.points.length === 0) {
      // New polygon
      state.selection.preview.points = [{ x, y }];
      state.drawing = true; // treat as drawing mode while collecting vertices
      drawSelectionPreview();
    } else if (!state.selection.active) {
      // Add vertex
      state.selection.preview.points.push({ x, y });
      drawSelectionPreview();
    } else {
      // If already active, allow drag move like other selections
      const dx = state.selection.transform.dx;
      const dy = state.selection.transform.dy;
      const adjusted = state.selection.vertices.map(([vx, vy]) => [vx + dx, vy + dy]);
      if (isPointInPolygon(x, y, adjusted)) {
        state.selection.isDragging = true;
        state.selection.dragStart = { x, y };
        state.selection.initialTransform = { ...state.selection.transform };
        canvas.setPointerCapture(e.pointerId);
        return;
      } else {
        // Click outside clears existing selection and starts new polygon
        clearSelection();
        state.selection.type = "polygonal";
        state.selection.preview.points = [{ x, y }];
        state.drawing = true;
      }
    }
    return;
  }
});

brushTypeSelect?.addEventListener("change", (e) => {
  state.brushType = e.target.value;
  state.currentStamp = null;
});


canvas.addEventListener("pointermove", (e) => {
  if (state.tool === "shapes" && state.drawing && state.shape.start) {
    const [x, y] = getCanvasXY(e);
    const a = state.shape.start, b = { x, y };
    if (state.shape.mode === "rect")    drawPreviewRect(a, b);
    if (state.shape.mode === "ellipse") drawPreviewEllipse(a, b);
    if (state.shape.mode === "line")    drawPreviewLine(a, b);
    return;
  }

  // Dragging active selection
  if (state.selection.isDragging && state.selection.dragStart && state.selection.initialTransform) {
    const [mouseX, mouseY] = getCanvasXY(e);
    const dragDx = mouseX - state.selection.dragStart.x;
    const dragDy = mouseY - state.selection.dragStart.y;

    state.selection.transform.dx = state.selection.initialTransform.dx + dragDx;
    state.selection.transform.dy = state.selection.initialTransform.dy + dragDy;

    drawSelectionPreview();
    return;
  }

  if (state.tool === "select_rect") {
    if (!state.drawing) return;
    const [x, y] = getCanvasXY(e);
    state.selection.preview.current = { x, y };
    drawSelectionPreview();
    return;
  }

  if (state.tool === "select_freeform" && state.drawing) {
    const [x, y] = getCanvasXY(e);
    state.selection.preview.points.push({ x, y });
    drawSelectionPreview();
    return;
  }

  if (state.tool === "select_polygonal" && state.drawing) {
    // Track hover for rubber-band preview
    const [x, y] = getCanvasXY(e);
    state.selection.preview.current = { x, y };
    drawSelectionPreview();
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

  // Stop dragging selection
  if (state.selection.isDragging) {
    state.selection.isDragging = false;
    state.selection.dragStart = null;
    canvas.releasePointerCapture(e.pointerId);
    return;
  }

  // Short-circuit pointerup for magnetic tool so we don't trigger stroke/send behavior
  if (state.tool === "select_magnetic") {
    // keep preview points intact until user finalizes with Enter
    state.drawing = false;
    try { canvas.releasePointerCapture(e.pointerId); } catch {}
    return;
  }

  if (state.tool === "select_rect") {
    const [x, y] = getCanvasXY(e);
    const start = state.selection.preview.start;

    // Selection coords
    state.selection.coords = [
      Math.min(start.x, x),
      Math.min(start.y, y),
      Math.max(start.x, x),
      Math.max(start.y, y)
    ];

    state.selection.active = true;
    state.drawing = false;

    // Clear preview since we have final data now
    state.selection.preview.start = null;
    state.selection.preview.current = null;

    // Optional for fetching selection mask from server
    await fetchSelectionMask();

    drawSelectionPreview();


    canvas.releasePointerCapture(e.pointerId);
    return;
    }

  if (state.tool === "select_freeform" && state.drawing) {
    const [x, y] = getCanvasXY(e);
    state.selection.preview.points.push({ x, y });

    state.selection.path = state.selection.preview.points.map(p => [p.x, p.y]);

    state.selection.active = true;
    state.drawing = false;

    // Clear preview data
    state.selection.preview.points = [];

    await fetchSelectionMask();

    drawSelectionPreview();

    canvas.releasePointerCapture(e.pointerId);
    return;
  }

  if (state.tool === "select_polygonal" && state.drawing) {
    // Finish polygon on double-click or Enter handled separately; pointerup does not finalize
    // If user double-clicks quickly (detail===2) and >=3 points, we finalize here too
    if (e.detail === 2 && state.selection.preview.points.length >= 3) {
      state.selection.vertices = state.selection.preview.points.map(p => [p.x, p.y]);
      state.selection.active = true;
      state.drawing = false;
      state.selection.preview.current = null;
      state.selection.preview.points = [];
      await fetchSelectionMask();
      drawSelectionPreview();
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

document.addEventListener("keydown", async (e) => {
  // can add keybinds for undo here

  // Special-case: allow finalizing polygon while drawing BEFORE active-check
  if (state.tool === "select_polygonal" && state.drawing) {
    if (e.key === "Enter" && state.selection.preview.points.length >= 3) {
      e.preventDefault();
      state.selection.vertices = state.selection.preview.points.map(p => [p.x, p.y]);
      state.selection.active = true;
      state.drawing = false;
      state.selection.preview.current = null;
      state.selection.preview.points = [];
      await fetchSelectionMask();
      drawSelectionPreview();
      return;
    }
  }

  // Special-case: allow finalizing magnetic selection and undo even after pointerup
  if (state.tool === "select_magnetic" && state.selection.raw_clicks) {
    if (e.key === "Enter" && state.selection.raw_clicks.length >= 3) {
      e.preventDefault();
      await finalizeMagneticSelection();
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      // delete last point
      if (state.selection.raw_clicks && state.selection.raw_clicks.length > 0) {
        state.selection.raw_clicks.pop();
        state.selection.preview.points = state.selection.raw_clicks.map(([x, y]) => ({ x, y }));
        drawSelectionPreview();
      }
      return;
    }
    if (e.key === "Escape") {
      // allow user to cancel the raw-click preview with Escape
      e.preventDefault();
      state.selection.raw_clicks = [];
      state.selection.preview.points = [];
      state.drawing = false;
      drawSelectionPreview();
      return;
    }
  }

  // Only if there is an active selection
  if (!state.selection.active) return;

  // CTRL+C - copy
  if (e.ctrlKey && e.key === "c") {
    e.preventDefault();
    await copySelection();
    return;
  }

  // CTRL+X - cut/move
  if (e.ctrlKey && e.key === "x") {
    e.preventDefault();
    await cutSelection();
    return;
  }

  // CTRL+V - paste
  if (e.ctrlKey && e.key === "v") {
    e.preventDefault();
    await pasteSelection();
    return;
  }

  // Delete - clear selection
  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    await deleteSelection();
    return;
  }

  // Enter - commit current transform
  if (e.key === "Enter") {
    e.preventDefault();
    await commitSelection();
    return;
  }

  // Escape - cancel selection
  if (e.key === "Escape") {
    e.preventDefault();
    await clearSelection();
    return;
  }
});


setActiveTool("brush");
updateShapeUI();
