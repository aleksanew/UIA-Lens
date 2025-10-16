# Handles image operations (resize, crop, filter, combine layers) using Pillow/OpenCV.
import numpy as np
import cv2
import base64
from flask import current_app

def process_image(image_id):
    """Load image from storage based on image_id?"""
    """Not sure how this works yet, placeholder for now"""
    img = cv2.imread('tests/test_image.png')
    return img

# def apply_grayscale(...): ...
# def apply_gaussian(...): ...

def create_mask(height, width):
    """Helper to create a blank mask."""
    return np.zeros((height, width), dtype=np.uint8)

def encode_mask(mask):
    """Encode mask as base64 PNG."""
    _, buffer = cv2.imencode('.png', mask)
    return base64.b64encode(buffer).decode('utf-8')

def rectangular_select(image_id, coords):
    img = process_image(image_id) # Load image
    height, width = img.shape[:2] # Get dimensions
    x1, y1, x2, y2 = coords # Unpack coords
    mask = create_mask(height, width) # Create blank mask
    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1) # Fill rectangle on mask
    return encode_mask(mask)

def freeform_select(image_id, path):
    img = process_image(image_id)
    height, width = img.shape[:2]
    path = np.array(path, np.int32) # Convert path to numpy array
    mask = create_mask(height, width)
    cv2.fillPoly(mask, [path], 255) # Fill polygon defined by path
    return encode_mask(mask)

def polygonal_select(image_id, vertices):
    img = process_image(image_id)
    height, width = img.shape[:2]
    vertices = np.array(vertices, np.int32) # Convert vertices to numpy array
    mask = create_mask(height, width)
    cv2.fillPoly(mask, [vertices], 255) # Fill polygon defined by vertices
    return encode_mask(mask)

def magic_lasso_select(image_id, seed_points):
    img = process_image(image_id)
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # Grayscale
    edges = cv2.Canny(gray, 50, 150) # Edge detection, adjust thresholds as needed, but adjusting didnt seem to fix much its just bad
    path = []
    seed_points = seed_points + [seed_points[0]]  # Close loop
    for i in range(len(seed_points) - 1): # loop through seed points, for each calculate distance and interpolate points between them
        start, end = seed_points[i], seed_points[i+1]
        start_arr, end_arr = np.array(start), np.array(end)
        distance = np.linalg.norm(end_arr - start_arr)
        num_steps = int(distance / 5) + 1 if distance > 0 else 1
        line_path = np.linspace(start_arr, end_arr, num=num_steps, dtype=int)
        for pt in line_path:
            snapped = False
            for r in range(1, 30):  # search radially up to 30 pixels for edge intersection, can adjust but doesnt seem to help much
                circle = np.zeros_like(edges)
                cv2.circle(circle, tuple(pt), r, 255, 1)
                intersects = cv2.bitwise_and(edges, circle)
                if np.any(intersects): # snap to strongest edge point
                    max_val = np.max(intersects)
                    snap_pt_idx = np.argwhere(intersects == max_val)[0]
                    snap_pt = snap_pt_idx[::-1]  # (y,x) to (x,y)
                    path.append(snap_pt.tolist())  # As list
                    snapped = True
                    break
            if not snapped: # if no edge found, just use original point
                path.append(pt.tolist())
    path = np.array(path, np.int32) # Convert path to numpy array
    mask = create_mask(height, width)
    if len(path) >= 3:
        cv2.fillPoly(mask, [path], 255) # Fill polygon defined by path
    return encode_mask(mask)
# Soltution chosen to be lightweight but not very good at all, will improve

# def brush_stroke(...): ...
# def eraser_stroke(...): ...
