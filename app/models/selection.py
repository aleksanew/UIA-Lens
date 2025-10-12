import numpy as np
import cv2
import base64

class SelectionMask:
    def __init__(self, mask_array: np.ndarray):
        self.mask = mask_array

    def apply_to_image(self, img: np.ndarray) -> np.ndarray:
        return cv2.bitwise_and(img, img, mask=self.mask) # Applies mask to image keeps selected area

    def encode(self) -> str:
        _, buffer = cv2.imencode('.png', self.mask)
        return base64.b64encode(buffer).decode('utf-8') # Encode mask as base64 PNG to send over api

    def validate(self) -> bool:
        return self.mask.ndim == 2 and self.mask.dtype == np.uint8 and np.all((self.mask == 0) | (self.mask == 255)) # checks if valid mask