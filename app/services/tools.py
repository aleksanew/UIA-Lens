import cv2
import numpy as np

def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (b, g, r) # OpenCV uses BGR format

def bgr_to_hex(b, g, r):
    return f"#{r:02x}{g:02x}{b:02x}"


def _ensure_bgra(img):
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img




def create_soft_round_stamp(size: int) -> np.ndarray:
    stamp = np.zeros((size, size), dtype=np.float32)
    center = size // 2
    
    for y in range(size):
        for x in range(size):
            distance = np.sqrt((x - center)**2 + (y - center)**2)
            stamp[y, x] = np.exp(-(distance**2) / (2 * (size/4)**2))
    
    return stamp

def create_chalk_stamp(size: int) -> np.ndarray:
    stamp = create_soft_round_stamp(size)
    
     # Add fine-grained noise for chalk texture
    noise = np.random.rand(size, size)
    noise = (noise > 0.4).astype(np.float32)
    stamp = stamp * (0.6 + noise * 0.4)
    
   # Add larger "holes" for chalk effect
    large_noise = np.random.rand(size, size) > 0.85
    stamp = stamp * (1 - large_noise * 0.7)
    
    return stamp

def create_watercolor_stamp(size: int) -> np.ndarray:
    """Akvarellaktig brush med bløte, flytende kanter"""
    stamp = np.zeros((size, size), dtype=np.float32)
    center = size // 2
    
    # Create multiple layers with different radii for "bleeding" effect
    for radius_factor in [0.5, 0.7, 0.9, 1.1]:
        layer = np.zeros((size, size), dtype=np.float32)
        for y in range(size):
            for x in range(size):
                distance = np.sqrt((x - center)**2 + (y - center)**2)
                target_radius = (size / 2) * radius_factor
                layer[y, x] = max(0, 1 - (distance / target_radius))
        
        # Add organic deformation with noise
        noise = np.random.rand(size, size) * 0.3
        layer = layer * (0.8 + noise)
        
        # Combine layers with decreasing intensity
        stamp = np.maximum(stamp, layer * (1.0 / radius_factor))
    
    # Clamp values before blur to prevent overflow
    stamp = np.clip(stamp, 0.0, 1.0)
    
    stamp = cv2.GaussianBlur(stamp, (3, 3), 2)
    
    return stamp


def apply_stamp(img: np.ndarray, x: int, y: int, stamp: np.ndarray, 
                color: tuple, opacity: float = 1.0):
    h, w = stamp.shape
    half_h, half_w = h // 2, w // 2
    
    # Calculate target region in image
    y1 = max(0, y - half_h)
    y2 = min(img.shape[0], y + half_h)
    x1 = max(0, x - half_w)
    x2 = min(img.shape[1], x + half_w)
    
    # Calculate corresponding region in stamp
    sy1 = half_h - (y - y1)
    sy2 = half_h + (y2 - y)
    sx1 = half_w - (x - x1)
    sx2 = half_w + (x2 - x)
    
    # Early exit if region is invalid
    if y2 <= y1 or x2 <= x1 or sy2 <= sy1 or sx2 <= sx1:
        return
    
    stamp_region = stamp[sy1:sy2, sx1:sx2]
    
    # Blend colors 
    for c in range(3):  # BGR channels
        img[y1:y2, x1:x2, c] = (
            img[y1:y2, x1:x2, c] * (1 - stamp_region * opacity) +
            color[c] * stamp_region * opacity
        ).astype(np.uint8)
    
    # update alpha channel
    img[y1:y2, x1:x2, 3] = np.maximum(
        img[y1:y2, x1:x2, 3],
        (stamp_region * opacity * 255).astype(np.uint8)
    )


def create_star_stamp(size: int) -> np.ndarray:
    stamp = np.zeros((size, size), dtype=np.uint8)
    center = size // 2
    outer_radius = size // 2
    inner_radius = outer_radius // 2.5

    # Generate star points
    points = []
    for i in range(10):
        angle = (i * np.pi / 5) - (np.pi / 2) 
        radius = outer_radius if i % 2 == 0 else inner_radius
        x = int(center + radius * np.cos(angle))
        y = int(center + radius * np.sin(angle))
        points.append([x, y])
    
    points = np.array(points, np.int32)
    
    cv2.fillPoly(stamp, [points], 255)
    
    stamp = stamp.astype(np.float32) / 255.0
    
    return stamp


def tool_brush(image_path: str, color: str, size: int, points: list[list[int]], 
               brush_type: str = "hard"):

    if not points or len(points) < 2:
        return

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not open picture: {image_path}")

    img = _ensure_bgra(img)
    bgr_color = hex_to_bgr(color)
    
    # if hard brush, use simple line drawing
    if brush_type == "hard":
        bgra_color = (*bgr_color, 255)
        for i in range(len(points) - 1):
            x1, y1 = map(int, points[i])
            x2, y2 = map(int, points[i+1])
            cv2.line(img, (x1, y1), (x2, y2), bgra_color, thickness=size, lineType=cv2.LINE_AA)
        cv2.imwrite(image_path, img)
        return
    
    # if not hard, create stamp based on brush type
    if brush_type == "chalk":
        stamp = create_chalk_stamp(size)
    elif brush_type == "watercolor":
        stamp = create_watercolor_stamp(size)
    elif brush_type == "star":
        stamp = create_star_stamp(size)
    else:
        stamp = create_soft_round_stamp(size)
    
    # Spacing for smooth strokes
    spacing = 0.25
    
    if brush_type == "star":
        spacing = 3
    
    # interpolate points and apply stamp
    for i in range(len(points) - 1):
        x1, y1 = map(int, points[i])
        x2, y2 = map(int, points[i + 1])
        
        distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        num_steps = max(1, int(distance / (size * spacing)))
        
        for step in range(num_steps + 1):
            t = step / max(1, num_steps)
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            
            apply_stamp(img, x, y, stamp, bgr_color, opacity=1.0)
    
    # Apply stamp at last point to ensure coverage
    x, y = map(int, points[-1])
    apply_stamp(img, x, y, stamp, bgr_color, opacity=1.0)
    
    cv2.imwrite(image_path, img)
    
def tool_eraser(image_path: str, size: int, points: list[list[int]], is_background: bool = False):
    if not points or len(points) < 2:
        return

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not open picture: {image_path}")

    img = _ensure_bgra(img)
    
    # If background layer, erase to white, else erase to transparent
    if is_background:
        erase_color = (255, 255, 255, 255)  
    else:
        erase_color = (0, 0, 0, 0)  # Transparent
    
    for i in range(len(points) - 1):
        x1, y1 = map(int, points[i])
        x2, y2 = map(int, points[i+1])
        cv2.line(img, (x1, y1), (x2, y2), erase_color, thickness=size, lineType=cv2.LINE_AA)

    cv2.imwrite(image_path, img)
    

    

def tool_bucket(image_path: str, color: str, start_point: list[int], tolerance: int = 10):
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not open picture: {image_path}")
    
    img = _ensure_bgra(img)
    h, w = img.shape[:2]
    x, y = map(int, start_point)
    
    if not (0 <= x < w and 0 <= y < h):
        raise ValueError(f"start_point out of bounds: ({x},{y}) not in [0..{w-1}]x[0..{h-1}]")

    new_bgr = hex_to_bgr(color)
    
    # Check if the target color is the same as new color
    if tuple(img[y, x, :3]) == tuple(new_bgr):
        return

    # Fill using floodFill
    bgr_img = img[:, :, :3].copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(bgr_img, mask, (x, y), new_bgr, 
                  loDiff=(tolerance,)*3, upDiff=(tolerance,)*3)

    # Updates to original image
    img[:, :, :3] = bgr_img
    filled = mask[1:-1, 1:-1] > 0
    img[filled, 3] = 255

    cv2.imwrite(image_path, img)