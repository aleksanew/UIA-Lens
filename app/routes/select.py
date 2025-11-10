# Endpoints for selection operations.

from flask import Blueprint, jsonify, request, session, current_app
from ..services.imaging import decode_mask, rectangular_select, freeform_select, polygonal_select
from app.services import storage, transform
import base64
import numpy as np
import cv2
import os

bp = Blueprint("select", __name__) # Blueprint for selection routes (dont really understand how this works cuz web app doesnt load when i use these routes)

# 4 routes for 4 selection types
@bp.post("/rect")
def rect():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401
    
    data = request.get_json()
    if not data or 'coords' not in data:
        return jsonify({"error": "Missing coords (x1, y1, x2, y2)"}), 400 # error if missing data
    try:
        mask_data = rectangular_select(pid, data['coords']) # call function from imaging.py
        return jsonify({"mask": mask_data}), 200 # return mask data as json
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # error if exception

# Same comments apply except its path instead of coords
@bp.post("/freeform")
def freeform():
    data = request.get_json()
    if not data or 'image_id' not in data or 'path' not in data:
        return jsonify({"error": "Missing image_id or path (list of [x,y] points)"}), 400
    try:
        mask_data = freeform_select(data['image_id'], data['path'])
        return jsonify({"mask": mask_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Same comments apply except its vertices instead of path
@bp.post("/polygonal")
def polygonal():
    data = request.get_json()
    if not data or 'image_id' not in data or 'vertices' not in data:
        return jsonify({"error": "Missing image_id or vertices (list of [x,y] points)"}), 400
    try:
        mask_data = polygonal_select(data['image_id'], data['vertices'])
        return jsonify({"mask": mask_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.post("/magnetic")
def magnetic():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401

    data = request.get_json()
    raw_clicks = data.get("raw_clicks")
    if not isinstance(raw_clicks, list) or len(raw_clicks) < 3:
        return jsonify({"error": "raw_clicks must be a list of at least 3 [x,y] points"}), 400
    
    try:
        from ..services.imaging import magnetic_finalize
        path, mask_b64, modes = magnetic_finalize(pid, raw_clicks)
        return jsonify({"mask": mask_b64,
                        "path": path,
                        "segment_modes": modes}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/apply")
def apply_selection():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401
    
    data = request.get_json()
    if not data or 'operation' not in data or 'selection' not in data or 'transform' not in data:
        return jsonify({"error": "Missing operation, selection, or transform"}), 400
    operation = data.get('operation')
    selection = data.get('selection')

    stack = storage.load_layers()
    trans = data.get('transform')
    src_layer = data.get('src_layer', stack.selected_layer()) #default to current
    dst_layer = data.get('dst_layer', stack.selected_layer())
        
    selection_type = selection.get('type')
    # Call appropriate selection function
    try:
        if selection_type == 'rect':
            if 'coords' not in selection:
                return jsonify({"error": "Missing coords for rectangular selection"}), 400
            mask_base64 = rectangular_select(pid, selection['coords'])
        elif selection_type == 'freeform':
            if 'path' not in selection:
                return jsonify({"error": "Missing path for freeform selection"}), 400
            mask_base64 = freeform_select(pid, selection['path'])
        elif selection_type == 'polygonal':
            if 'vertices' not in selection:
                return jsonify({"error": "Missing vertices for polygonal selection"}), 400
            mask_base64 = polygonal_select(pid, selection['vertices'])
        elif selection_type == 'magnetic':
            # Accept either finalized vertices or raw_clicks produced by the magnetic tool.
            # If vertices are present (frontend finalized), reuse polygonal_select for mask.
            if 'vertices' in selection:
                mask_base64 = polygonal_select(pid, selection['vertices'])
            elif 'raw_clicks' in selection:
                try:
                    from ..services.imaging import magnetic_finalize
                    path, mask_b64, modes = magnetic_finalize(pid, selection['raw_clicks'])
                    mask_base64 = mask_b64
                    # Optionally update selection vertices in-place (not persisted across request)
                    selection['vertices'] = path
                except Exception:
                    raise
            else:
                return jsonify({"error": "Missing vertices or raw_clicks for magnetic selection"}), 400
        else:
            return jsonify({"error": "Invalid selection type"}), 400
    except Exception as e:
        return jsonify({"error": f"Selection processing failed: {str(e)}"}), 500
    # Decode base64 to numpy array
    mask = decode_mask(mask_base64)
    if mask is None:
        return jsonify({"error": "Failed to decode selection mask"}), 500
    
    stack = storage.load_layers()
    src_layer = stack.get_current_layer()
    src_image = src_layer.get_image()
    if src_image is None:
        return jsonify({"error": f"Failed to load source layer image at {src_layer}"}), 500

    if operation == "transform":
        scale = trans.get('scale', 1.0)
        rotation_deg = trans.get('rotation', 0)

        src_img = transform.rotate(src_image, mask, int(rotation_deg))

        bgra_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGRA)
        bgra_mask = transform.rotate(bgra_mask, mask, int(rotation_deg))
        mask = cv2.cvtColor(bgra_mask, cv2.COLOR_BGRA2GRAY)

        src_img = transform.rescale(src_img, mask, float(scale))

        src_layer.update(src_img)
        storage.save_layers(stack)
        storage.redraw_selected_image(stack)

        return jsonify({"status": "ok"}), 200

    if src_image.ndim == 2:
        src_image = cv2.cvtColor(src_image, cv2.COLOR_GRAY2BGRA)
    elif src_image.shape[2] == 3:
        src_image = cv2.cvtColor(src_image, cv2.COLOR_BGR2BGRA)

    # Extract selected region using the mask
    # The mask is grayscale (255 = selected, 0 = not selected)

    # Find bounding box of the selection (for efficiency, avoids working with entire image)
    coords = cv2.findNonZero(mask)
    if coords is None:
        return jsonify({"error": "Empty selection"}), 400

    x, y, w, h = cv2.boundingRect(coords)

    # Extract the bounding box region from source image and mask
    selected_region = src_image[y:y+h, x:x+w].copy()
    mask_region = mask[y:y+h, x:x+w]

    # Apply mask to the region (use mask as alpha channel)
    # This creates a region with transparency where not selected
    mask_4channel = cv2.merge([mask_region, mask_region, mask_region, mask_region])
    selected_region = cv2.bitwise_and(selected_region, mask_4channel)

    # Get transform parameters
    dx = trans.get('dx', 0)
    dy = trans.get('dy', 0)
    scaleX = trans.get('scaleX', 1.0)
    scaleY = trans.get('scaleY', 1.0)

    # Apply scaling if needed
    if scaleX != 1.0 or scaleY != 1.0:
        new_w = int(w * scaleX)
        new_h = int(h * scaleY)
        selected_region = cv2.resize(selected_region, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        mask_region = cv2.resize(mask_region, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        w, h = new_w, new_h

    # Calculate new position
    new_x = x + dx
    new_y = y + dy

    # Handle "move" operation, start by removing source region
    if operation == 'move':
        src_image[y:y+h, x:x+w] = cv2.bitwise_and(
            src_image[y:y+h, x:x+w],
            cv2.bitwise_not(mask_4channel)
        )

        # If this is a pure cut (no translation or scaling), persist once and finish
        if (dx == 0 and dy == 0 and float(scaleX) == 1.0 and float(scaleY) == 1.0):
            layer = stack.get_current_layer()
            layer.update(src_image)
            storage.save_layers(stack)
            storage.redraw_selected_image(stack)
            return jsonify({"status": "ok", "action": "cut"}), 200
    
    # Destination is current layer (same as source in current implementation)
    dst_layer = src_layer
    dst_image = src_image
    if dst_image is None:
        return jsonify({"error": f"Failed to load destination layer image at {dst_layer}"}), 500
    
    # Ensure format
    if dst_image.ndim == 2:
        dst_image = cv2.cvtColor(dst_image, cv2.COLOR_GRAY2BGRA)
    elif dst_image.shape[2] == 3:
        dst_image = cv2.cvtColor(dst_image, cv2.COLOR_BGR2BGRA)
    
    # Get image dimensions
    dst_h, dst_w = dst_image.shape[:2]

    # Check if new position is within bounds (to clip)
    new_x = max(0, min(new_x, dst_w - 1))
    new_y = max(0, min(new_y, dst_h - 1))

    # How much fits
    paste_w = min(w, dst_w - new_x)
    paste_h = min(h, dst_h - new_y)

    if paste_w > 0 and paste_h > 0:
        # ready to put selection on destination
        region_to_paste = selected_region[:paste_h, :paste_w]

        # Use the mask as alpha for blending
        alpha = mask_region[:paste_h, :paste_w].astype(float) / 255.0
        alpha_3d = np.stack([alpha,alpha,alpha,alpha],axis=2)

        #Blend the region onto destination
        dst_region = dst_image[new_y:new_y+paste_h, new_x:new_x+paste_w]
        blended = (region_to_paste * alpha_3d + dst_region * (1 - alpha_3d)).astype(np.uint8)
        dst_image[new_y:new_y+paste_h, new_x:new_x+paste_w] = blended

    # Save updated destination layer
    stack = storage.load_layers()
    layer = stack.get_current_layer()
    layer.update(dst_image)
    storage.save_layers(stack)
    storage.redraw_selected_image(stack)

    return jsonify({"status": "ok"}), 200


@bp.post("/delete")
def delete_selection():
    pid = session.get("pid")
    if not pid:
        return jsonify({"error": "Not logged in / missing pid"}), 401
    
    data = request.get_json()
    if not data or 'selection' not in data:
        return jsonify({"error": "Missing selection"}), 400

    selection = data.get('selection')

    stack = storage.load_layers()
    src_layer = stack.get_current_layer()
    src_image = src_layer.get_image()
    if src_image is None:
        return jsonify({"error": f"Failed to load source layer image at {src_layer}"}), 500

    sel_type = selection.get('type')
    try:
        if sel_type == 'rect':
            mask_base64 = rectangular_select(pid, selection['coords'])
        elif sel_type == 'freeform':
            mask_base64 = freeform_select(pid, selection['path'])
        elif sel_type == 'polygonal':
            mask_base64 = polygonal_select(pid, selection['vertices'])
        elif sel_type == 'magnetic':
            # Accept either finalized vertices or raw_clicks
            if 'vertices' in selection:
                mask_base64 = polygonal_select(pid, selection['vertices'])
            elif 'raw_clicks' in selection:
                from ..services.imaging import magnetic_finalize
                path, mask_b64, modes = magnetic_finalize(pid, selection['raw_clicks'])
                mask_base64 = mask_b64
            else:
                return jsonify({"error": f"Missing vertices or raw_clicks for magnetic selection"}), 400
        else:
            return jsonify({"error": f"Unknown selection type: {sel_type}"}), 400
    except Exception as e:
        return jsonify({"error": f"Selection failed: {e}"}), 500

    mask = decode_mask(mask_base64)
    if mask is None:
        return jsonify({"error": "Failed to decode selection mask"}), 500
    
    if src_image.ndim == 2:
        src_image = cv2.cvtColor(src_image, cv2.COLOR_GRAY2BGRA)
    elif src_image.shape[2] == 3:
        src_image = cv2.cvtColor(src_image, cv2.COLOR_BGR2BGRA)

    # Ensure mask is same size as source image
    src_h, src_w = src_image.shape[:2]
    mask_h, mask_w = mask.shape[:2]
    
    if mask_h != src_h or mask_w != src_w:
        # Resize mask to match source image
        mask = cv2.resize(mask, (src_w, src_h), interpolation=cv2.INTER_NEAREST)
    

    mask_4channel = cv2.merge([mask, mask, mask, mask])
    res_image = cv2.bitwise_and(src_image, cv2.bitwise_not(mask_4channel))
                                
    stack = storage.load_layers()
    layer = stack.get_current_layer()
    layer.update(res_image)
    storage.save_layers(stack)
    storage.redraw_selected_image(stack)

    return jsonify({"status": "ok"}), 200