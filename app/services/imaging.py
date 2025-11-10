# Handles image operations (resize, crop, filter, combine layers) using Pillow/OpenCV.
import numpy as np
import cv2
import base64
from flask import current_app
from app.services import storage
import time

# Magnetic lassso heuristics, i assume these can be endlessly tweaked for slight improvements
ARC_MIN_CONTOUR_POINTS = 12   # minimum points in a contour to count it
MAX_ARC_RATIO = 4.0           # maximum arc length over euclidian distance
LOOP_FACTOR = 0.6             # arc cant be more than 60% of the full contour perimeter
CURVATURE_SPIKE_DEG = 150     # Angle threshold for detecting sharp turns
CURVATURE_SPIKE_MAX = 3       # Maximum allowed sharp turns in an arc
MAX_CONTOUR_DIST = 15          # max pixel distance to snap to a contour point
SNAP_RADIUS = 20              # search radius for edge snapping
CANNY_LOW = 50                # canny edge detection low threshold
CANNY_HIGH = 150              # canny edge detection high threshold

# Cache for edge structures
_EDGE_CACHE = {}

def compute_edge_structures(pid, layer_index=None):
    """
    Compute or retrieve cached
    """
    stack = storage.load_layers()
    if stack is None:
        raise RuntimeError("No layer stack available for compute_edge_structures")

    # If no specific layer_index supplied, use currently selected layer
    if layer_index is None:
        layer_index = stack.selected_layer()

    # check for cache
    if pid in _EDGE_CACHE and layer_index in _EDGE_CACHE[pid]:
        return _EDGE_CACHE[pid][layer_index]

    # get layer via LayerStack API
    layer = stack.at(layer_index)
    if layer is None:
        raise IndexError(f"Layer index out of range: {layer_index}")

    img = layer.get_image()

    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)

    # Find contours, CHAIN_APPROX_NONE is dense points, no simplification
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    # Precompute contour lengths for loop detection
    contour_lengths = [cv2.arcLength(cnt, True) for cnt in contours]

    # Connected components for same edge grouping
    _, component_labels = cv2.connectedComponents(edges, connectivity= 8)

    # package
    edge_data = {
        'edges': edges,
        'contours': contours,
        'contour_lengths': contour_lengths,
        'component_labels': component_labels,
        'timestamp': time.time()
    }

    # store in cache
    if pid not in _EDGE_CACHE:
        _EDGE_CACHE[pid] = {}
    _EDGE_CACHE[pid][layer_index] = edge_data

    return edge_data

def invalidate_edge_cache(pid, layer_index=None):
    """Invalidate cached edge structures for a user/session."""
    if pid in _EDGE_CACHE:
        if layer_index is None:
            del _EDGE_CACHE[pid]
        elif layer_index in _EDGE_CACHE[pid]:
            del _EDGE_CACHE[pid][layer_index]

def snap_to_edge(point, edge_data, radius=SNAP_RADIUS):
    """Snap a point to the nearest edge within a given radius."""
    x, y = int(point[0]), int(point[1])
    edges = edge_data['edges']
    h, w = edges.shape

    x0 = max(0, x - radius)
    y0 = max(0, y - radius)
    x1 = min(w - 1, x + radius)
    y1 = min(h - 1, y + radius)

    roi = edges[y0:y1+1, x0:x1+1]
    edge_pts = np.argwhere(roi > 0)

    if len(edge_pts) == 0:
        return (x, y)  # No edge found, return original point
    
    edge_pts_abs = edge_pts + np.array([y0, x0])  # Adjust to image coords

    dist = np.sum((edge_pts_abs - np.array([y, x]))**2, axis=1)
    min_idx = np.argmin(dist)
    snap_y, snap_x = edge_pts_abs[min_idx]

    return (int(snap_x), int(snap_y))

def find_contour_index(point, contours, max_dist=MAX_CONTOUR_DIST):
    """Find the index of the contour closest to the point within max_dist."""
    px, py = point
    
    for cid, cnt in enumerate(contours):
        pts = cnt.reshape(-1, 2) # reshape to [[x,y], ...]
        for i, (cx, cy) in enumerate(pts):
            d2 = (cx - px)**2 + (cy - py)**2
            if d2 <= max_dist**2:
                return cid, i # fount index
    return None, None # not found

def extract_contour_arc(contours, cid, i1, i2):
    """Extract arc points between two indices on a contour"""
    cnt = contours[cid].reshape(-1, 2)
    n = len(cnt)

    # forward arc
    if i2 >= i1:
        arc_fwd = cnt[i1:i2+1].tolist()
    else:
        arc_fwd = np.concatenate((cnt[i1:], cnt[:i2+1]), axis=0).tolist()

    # backward arc
    if i1 >= i2:
        arc_bwd = cnt[i2:i1+1][::-1].tolist()
    else:
        arc_bwd = np.concatenate((cnt[i2:], cnt[:i1+1]), axis=0)[::-1].tolist()
    
    return arc_fwd, arc_bwd

def validate_arc(arc, p1, p2, contour_perimeter, heuristics):
    """Check if an arc is valid using heuristics"""

    if len(arc) < 2:
        return False
    
    # heuristic 1: minimum points to avoid noise
    if len(arc) < heuristics['ARC_MIN_CONTOUR_POINTS']:
        return False
    
    # Heuristic 2: arc length vs straight line distance
    arc_length = len(arc)
    euclid_dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    if euclid_dist > 0:
        ratio = arc_length / euclid_dist
        if ratio > heuristics['MAX_ARC_RATIO']:
            return False # Arc is taking a huge detour

    # Heuristic 3: loop avoidance
    if contour_perimeter > 0:
        if arc_length > heuristics['LOOP_FACTOR'] * contour_perimeter:
            return False # Arc is too long, likely looping around 

    # Heuristic 4: curvature spikes (crossing edges)
    if len(arc) >= 3:
        spike_count = 0
        for i in range(1, len(arc)-1):
            # calculate angle at point
            v1 = np.array(arc[i]) - np.array(arc[i-1])
            v2 = np.array(arc[i+1]) - np.array(arc[i]) 

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 < 1e-6 or norm2 < 1e-6:
                continue   # skip if vectors are too small

            # dot product to angle
            cos_angle = np.dot(v1, v2) / (norm1 * norm2)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle_deg = np.degrees(np.arccos(cos_angle))

            if angle_deg > heuristics['CURVATURE_SPIKE_DEG']:
                spike_count += 1
                if spike_count > heuristics['CURVATURE_SPIKE_MAX']:
                    return False # too many sharp turns

    return True # passed all current heuristics

def connect_vertices(p1, p2, edge_data, heuristics):
    """Connect two points using the best available method"""

    # snap to edges
    s1 = snap_to_edge(p1, edge_data)
    s2 = snap_to_edge(p2, edge_data)

    # find which contours they landed on
    cid1, i1 = find_contour_index(s1, edge_data['contours'])
    cid2, i2 = find_contour_index(s2, edge_data['contours'])

    # check if same contour
    if cid1 is None or cid2 is None or cid1 != cid2:
        # Different contours or not on any, fallback method
        return "fallback", [list(s1), list(s2)]
    
    # extract both dimensions
    arc_fwd, arc_bwd = extract_contour_arc(edge_data['contours'], cid1, i1, i2)
    contour_perimeter = edge_data['contour_lengths'][cid1]

    # validate forward and backward
    if validate_arc(arc_fwd, s1, s2, contour_perimeter, heuristics):
        return "arc", arc_fwd
    if validate_arc(arc_bwd, s1, s2, contour_perimeter, heuristics):
        return "arc", arc_bwd
    
    # neither arc valid, fallback
    return "fallback", [list(s1), list(s2)]

def magnetic_finalize(pid, raw_clicks):
    """Convert raw user clicks into a magenetic lasso path and mask"""
    if not raw_clicks or len(raw_clicks) < 3:
        # return empty mask for too few points, need 3 for polygon
        stack = storage.load_layers()
        h, w = stack.shape()
        empty = np.zeros((h, w), dtype=np.uint8)
        return [], encode_mask(empty), []
    
    edge_data = compute_edge_structures(pid)

    heuristics = {
        'ARC_MIN_CONTOUR_POINTS': ARC_MIN_CONTOUR_POINTS,
        'MAX_ARC_RATIO': MAX_ARC_RATIO,
        'LOOP_FACTOR': LOOP_FACTOR,
        'CURVATURE_SPIKE_DEG': CURVATURE_SPIKE_DEG,
        'CURVATURE_SPIKE_MAX': CURVATURE_SPIKE_MAX
    }

    # close click loop, pair last to first
    clicks_closed = raw_clicks + [raw_clicks[0]]

    magnetic_path = []
    segment_modes = []

    for i in range(len(clicks_closed) - 1):
        p1 = clicks_closed[i]
        p2 = clicks_closed[i+1]
        mode, seg_pts = connect_vertices(p1, p2, edge_data, heuristics)
        segment_modes.append(mode)

        if i == 0:
            magnetic_path.extend(seg_pts)
        else:
            # avoid duplicating points if its the same as previous segment end
            if magnetic_path and seg_pts:
                last = magnetic_path[-1]
                first = seg_pts[0]
                if last[0] == first[0] and last[1] == first[1]:
                    magnetic_path.extend(seg_pts[1:])
                else:
                    magnetic_path.extend(seg_pts)
            else:
                magnetic_path.extend(seg_pts)

    # need at least 3 distinct points to fill
    stack = storage.load_layers()
    h, w = stack.shape()
    if len(magnetic_path) < 3:
        empty = np.zeros((h,w), dtype=np.uint8)
        return magnetic_path, encode_mask(empty), segment_modes
    
    poly = np.array(magnetic_path, np.int32)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [poly], 255) # Fill polygon defined by path
    mask_b64 = encode_mask(mask)

    return magnetic_path, mask_b64, segment_modes
     
def encode_mask(mask):
    """Encode mask as base64 PNG."""
    _, buffer = cv2.imencode('.png', mask)
    return base64.b64encode(buffer).decode('utf-8')

def rectangular_select(image_id, coords):
    stack = storage.load_layers()
    height, width = stack.shape()  # Get actual layer dimensions
    x1, y1, x2, y2 = map(int,coords) # Unpack coords
    x1 = max(0, min(x1, width  - 1))
    x2 = max(0, min(x2, width  - 1))
    y1 = max(0, min(y1, height - 1))
    y2 = max(0, min(y2, height - 1))
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1) # Fill rectangle on mask
    _, buffer = cv2.imencode('.png', mask)
    return base64.b64encode(buffer).decode('utf-8')

def freeform_select(image_id, path):
    stack = storage.load_layers()
    height, width = stack.shape()
    path = np.array(path, np.int32) # Convert path to numpy array
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [path], 255) # Fill polygon defined by path
    _, buffer = cv2.imencode('.png', mask)
    return base64.b64encode(buffer).decode('utf-8')

def polygonal_select(image_id, vertices):
    stack = storage.load_layers()
    height, width = stack.shape()
    vertices = np.array(vertices, np.int32) # Convert vertices to numpy array
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [vertices], 255) # Fill polygon defined by vertices
    _, buffer = cv2.imencode('.png', mask)
    return base64.b64encode(buffer).decode('utf-8')

def decode_mask(mask_data: str) -> np.ndarray:
    """Decode base64 PNG mask to numpy array."""
    mask_bytes = base64.b64decode(mask_data)
    nparr = np.frombuffer(mask_bytes, np.uint8)
    mask = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    return mask
