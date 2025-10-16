import copy
import cv2
from app.models import Layer
import numpy as np
import pickle

class LayerStack:

    # Creates and selects a white background layer
    def __init__(self, height, width):
        self._layer_array = np.array([])
        self._height = height
        self._width = width
        self._selected_layer = 0

    # adds background and layer 1
    def add_base_layers(self):
        white_image = np.full((self._height, self._width, 4), (255, 255, 255, 255), dtype=np.uint8)
        background_layer = Layer.Layer("Background", self._height, self._width)
        background_layer.update(white_image)
        self._layer_array = np.array([background_layer])
        self.create_layer()

    # Creates and selects a transparent background layer
    # Currently can produce duplicate layer names if layers have been deleted
    def create_layer(self):
        new_layer_number = np.size(self._layer_array)
        new_layer = Layer.Layer(f"Layer {new_layer_number}", self._height, self._width)
        self._layer_array = np.append(self._layer_array, new_layer)
        self._selected_layer = new_layer_number

    # Get number of layers
    def size(self):
        return np.size(self._layer_array)

    # Get layer_array[i]
    def at(self, i):
        if i >= np.size(self._layer_array):
            return 0
        return self._layer_array[i]

    def toggle_visible_at(self, i):
        if i >= np.size(self._layer_array):
            return False
        self._layer_array[i].toggle_visible()
        return True

    # Get currently selected layer
    def get_current_layer(self):
        if (self._selected_layer >= np.size(self._layer_array)) or (self._selected_layer < 0):
            return 0
        return self._layer_array[self._selected_layer]

    # Replace the currently selected layer
    def replace_current_layer(self, updated_layer):
        if self._selected_layer < 0:
            return
        self._layer_array[self._selected_layer] = updated_layer

    # Choose a layer to be "selected"
    def select_layer(self, i):
        if i >= np.size(self._layer_array):
            return
        self._selected_layer = i

    # Swap two layers
    def swap_layers(self, i, j):
        if (i or j) >= np.size(self._layer_array):
            return
        self._layer_array[i], self._layer_array[j] = self._layer_array[j], self._layer_array[i]

    # Delete layer at index
    def delete_layer(self, i):
        if i >= np.size(self._layer_array):
            return
        if i >= self._selected_layer:
            i = i-1
        self._layer_array = np.delete(self._layer_array, i)

    # Delete currently selected layer
    def delete_selected_layer(self):
        self._layer_array = np.delete(self._layer_array, self._selected_layer)
        self._selected_layer = np.size(self._layer_array) -1

    # Duplicate currently selected layer
    def duplicate_selected_layer(self):
        duplicate = copy.deepcopy(self._layer_array[self._selected_layer])
        duplicate.rename(f"{duplicate.name()} - copy")
        self._selected_layer = self._selected_layer + 1
        self._layer_array = np.insert(self._layer_array, self._selected_layer, duplicate)

    # Takes images from all layers and combine them, in order, to a single image
    def get_collapsed_stack_as_image(self):

        bottom_layer = self._layer_array[0]

        dst = bottom_layer.get_image().copy()

        for i, x in enumerate(self._layer_array):

            if i+1 == np.size(self._layer_array):
                break

            next_layer = self._layer_array[i+1]

            # Only add image not hidden
            if next_layer.is_hidden():
                continue

            background = dst
            foreground = next_layer.get_image().copy()

            # Separate color from alpha.
            # Results in one bgr image/array, and one alpha image/array
            cb = background[:, :, :3]           # [b, g, r]
            ab = background[:, :, 3] / 255.0    # normalized alpha

            ct = foreground[:, :, :3]           # [b, g, r]
            at = foreground[:, :, 3] / 255.0    # normalized alpha

            # Calculate alpha array for new image
            ao = at + ab * (1 - at)

            # Calculate color array for new image and adjust alpha based on "ao"
            # [:, :, None] turns alpha array shape from [height,width] to [height,width,1], allowing slicing
            # with the color array with shape [height,width,3]
            co = (ct * at[:, :, None] + cb * ab[:, :, None] * (1 - at[:, :, None])) / (ao[:, :, None] + 0.000001)

            # Apply color and alpha array to destination image
            dst[:, :, :3] = co
            # Turns alpha array from 0-1 to 0-255. Ensures correct type and a lower and upper limit
            dst[:, :, 3] = np.clip(ao * 255, 0, 255).astype(np.uint8)

        return dst

    # Unsure if filetype should be required in path.
    # Add/remove depending on what makes sense with load/save implementation
    def save_pickle(self, path):
        try:
            with open(f"{path}", "wb") as f:
                # noinspection PyTypeChecker
                pickle.dump(self, f)
                return True
        except Exception as e:
            print("error saving:", e)
            return False

    # Unsure if filetype should be required in path.
    # Add/remove depending on what makes sense with load/save implementation
    def load_pickle(self, path):
        with open(f"{path}", "rb") as f:
            try:
                db = pickle.load(f)
            except Exception as e:
                print("depickling error:", e)
                return False

            # Pickle must have correct structure
            if not isinstance(db, LayerStack):
                print("error in file content/structure")
                return False

            # All layers must have same height/width
            for i, x in enumerate(db._layer_array):
                h, w, d = x.get_image().shape
                if (h != db._height) or (w != db._width):
                    print("height or width mismatch")
                    return False

            self._layer_array = db._layer_array
            self._height = db._height
            self._width = db._width
            # Ensures selected layer is in bounds of array
            if db._selected_layer >= np.size(db._layer_array):
                self._selected_layer = np.size(db._layer_array) - 1
            else:
                self._selected_layer = db._selected_layer
            return True

    # Turns all image arrays into png to display on webpage
    def create_images_from_layers_at(self, folder):
        for i, x in enumerate(self._layer_array):
            cv2.imwrite(f"{folder}/Layer{i}.png", x.get_image())

    # Get object in form of json.
    # Will only return filename, and not images,
    # images must be stored first with "create_images_from_layers_at".
    # If changes are made after creating images, json might be incorrect
    def get_as_json(self):
        data = {
            "selected_layer": self._selected_layer,
            "height": self._height,
            "width": self._width,
            "layers": []
        }

        for i, x in enumerate(self._layer_array):
            layer_info = {
                "name": x.name(),
                "visible": int(not x.is_hidden()),
                "filename": f"Layer{i}.png"
            }
            data["layers"].append(layer_info)
        return data