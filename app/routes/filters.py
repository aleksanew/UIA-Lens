# Endpoints for image filters (blur, sharpen, grayscale, etc.).
import numpy as np

from app.services import filter, storage
from flask import Blueprint, jsonify, request, session

bp = Blueprint("filters", __name__)

@bp.post("/hue_shift")
def hue_shift():
    try:
        data = request.get_json()
        value = data.get("value")
        if not isinstance(value, int):
            return jsonify({"status": "Value not integer"}), 400

        stack = storage.load_layers()
        layer = stack.get_current_layer()
        img = layer.get_image()
        img = filter.hue_shift(img, value)
        layer.update(img)
        stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
        storage.save_layers(stack)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/grayscale")
def grayscale():
    stack = storage.load_layers()
    layer = stack.get_current_layer()
    img = layer.get_image()
    img = filter.grayscale(img)
    layer.update(img)
    stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
    storage.save_layers(stack)
    return jsonify({"status": "ok"}), 200


@bp.post("/feature_detection")
def feature_detection():
    print("a")
    try:
        data = request.get_json()
        block_size = int(data.get("block_size"))
        ksize = int(data.get("ksize"))
        k = float(data.get("k"))

        if not isinstance(block_size, int):
            return jsonify({"status": "Block size not integer"}), 400
        if block_size <= 0:
            return jsonify({"status": "Block size must be positive"}), 400
        if not isinstance(ksize, int):
            return jsonify({"status": "Ksize not float"}), 400
        if ksize > 31:
            return jsonify({"status": "Ksize must be less than 31"}), 400
        if ksize % 2 == 0:
            return jsonify({"status": "Ksize must be odd"}), 400
        if not isinstance(k, float):
            return jsonify({"status": "Ksize must be float"}), 400

        stack = storage.load_layers()
        layer = stack.get_current_layer()
        img = layer.get_image()
        img = filter.feature_detection(img, block_size, ksize, k)
        layer.update(img)
        stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
        storage.save_layers(stack)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/edge_detection")
def edge_detection():
    try:
        data = request.get_json()
        alg = str(data.get("algorithm"))
        if not isinstance(alg, str):
            return jsonify({"status": "Algorithm not string"}), 400

        stack = storage.load_layers()
        layer = stack.get_current_layer()
        img = layer.get_image()

        if alg == "sobel":
            img = filter.sobel_edge(img)
        elif alg == "laplace":
            img = filter.laplace_edge(img)
        elif alg == "canny":
            img = filter.canny_edge(img)
        else:
            return jsonify({"status": "Invalid algorithm"}), 400
        layer.update(img)
        stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
        storage.save_layers(stack)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/kernel_filter")
def kernel_filter():
    try:
        data = request.get_json()
        kernel = data.get("type")

        if not isinstance(kernel, list):
            return jsonify({"status": "Invalid kernel"}), 400
        kernel = np.array(kernel)

        stack = storage.load_layers()
        layer = stack.get_current_layer()
        img = layer.get_image()
        img = filter.kernel_filter(img, kernel)
        layer.update(img)
        stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
        storage.save_layers(stack)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/blur")
def blur():
    try:
        data = request.get_json()
        thresh_type = str(data.get("type"))
        thresh = int(data.get("threshold"))

        if not isinstance(thresh_type, str):
            return jsonify({"status": "Type not string"}), 400
        if not isinstance(thresh, int):
            return jsonify({"status": "Threshold not integer"}), 400
        if thresh_type not in ["binary", "binary_inv", "trunc", "tozero", "tozero_inv", "otsu", "triangle"]:
            return jsonify({"status": "Invalid thresholding type"}), 400

        stack = storage.load_layers()
        layer = stack.get_current_layer()
        img = layer.get_image()
        img = filter.threshold(img, thresh_type, thresh)
        layer.update(img)
        stack.create_image_from_selected_layers_at(f"users/{session["pid"]}/layers")
        storage.save_layers(stack)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500







