import numpy as np

class Layer:

    def __init__(self, name, height, width):
        self._name = name
        self._image = np.full((height, width, 4), (0, 0, 0, 0), dtype=np.uint8)
        self._visible = True

    def update(self, image):
        self._image = image

    def get_image(self):
        return self._image

    def rename(self, name):
        self._name = name

    def name(self):
        return self._name

    def hide(self):
        self._visible = False

    def show(self):
        self._visible = True

    def is_hidden(self):
        return not self._visible

    def toggle_visible(self):
        self._visible = not self._visible