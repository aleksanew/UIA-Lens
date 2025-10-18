# app/services/tools.py
import cv2
import numpy as np

def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (b, g, r)

def _ensure_bgra(img):
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img

def tool_brush(image_path: str, color: str, size: int, points: list[list[int]]):
    if not points or len(points) < 2:
        return

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not open picture: {image_path}")

    # Convert to BGRA if needed
    img = _ensure_bgra(img)

    # draw directly with cv2.line
    bgr_color = hex_to_bgr(color)
    bgra_color = (*bgr_color, 255)  # Full opacity
    
    for i in range(len(points) - 1):
        x1, y1 = map(int, points[i])
        x2, y2 = map(int, points[i+1])
        cv2.line(img, (x1, y1), (x2, y2), bgra_color, thickness=size, lineType=cv2.LINE_AA)

    cv2.imwrite(image_path, img)
    
def tool_eraser(image_path: str, size: int, points: list[list[int]]):
    if not points or len(points) < 2:
        return

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not open picture: {image_path}")

    # Convert to BGRA if needed
    img = _ensure_bgra(img)

    # draw directly with cv2.line
    transparent_color = (0, 0, 0, 0)  
    
    for i in range(len(points) - 1):
        x1, y1 = map(int, points[i])
        x2, y2 = map(int, points[i+1])
        cv2.line(img, (x1, y1), (x2, y2), transparent_color, thickness=size, lineType=cv2.LINE_AA)

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