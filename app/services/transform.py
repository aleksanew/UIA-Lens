import cv2
import numpy as np




def rotate(img, mask, deg):
    deg = deg % 360 # Ensure in bounds
    deg = 360 - deg # Makes rotation clockwise

    center = _find_center(mask)
    back = _blank_out(img, mask)
    fore = _extract(img, mask)
    fore = _rotate(fore, deg, center)
    img = _blend(back, fore)
    return img


def rescale(img, mask, scale):
    center = _find_center(mask)
    back = _blank_out(img, mask)
    fore = _extract(img, mask)
    fore = _rescale(fore, scale, center)
    img = _blend(back, fore)
    return img


# Extract part of an image based on mask.
# Extracted image has same shape as original (padded with (0,0,0,0))
def _extract(image, mask):
    # Ensure mask is binary 0/1
    mask_bin = (mask > 0).astype(np.uint8)

    # Extract colors and original alpha
    color = image[:, :, :3]
    alpha = image[:, :, 3] / 255.0 # from 0-255 to 0-1

    # Multiply original color by mask
    # color = (color * mask_bin[:, :, None]).astype(np.uint8)

    # Multiply alpha by mask
    alpha = (alpha * mask_bin).astype(np.float32)

    # Merge back to BGRA
    extracted = cv2.merge([
        color[:, :, 0],
        color[:, :, 1],
        color[:, :, 2],
        (alpha*255).astype(np.uint8) # from 0-1 to 0-255
        ])
    return extracted


# Blanks out part of an image based on mask
def _blank_out(image, mask):
    img = image.copy()
    mask_bin = (mask > 0)

    # Set RGB channels to 0
    img[mask_bin, 0] = 0  # Blue
    img[mask_bin, 1] = 0  # Green
    img[mask_bin, 2] = 0  # Red

    # Set alpha channel to 0
    img[mask_bin, 3] = 0

    return img


# Blend two images together
def _blend(back, fore):
    dst = back
    background = back
    foreground = fore

    # Separate color from alpha.
    # Results in one bgr image/array, and one alpha image/array
    cb = background[:, :, :3]  # [b, g, r]
    ab = background[:, :, 3] / 255.0  # normalized alpha

    ct = foreground[:, :, :3]  # [b, g, r]
    at = foreground[:, :, 3] / 255.0  # normalized alpha

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

# Finds the center point of a mask
def _find_center(mask):
    ys, xs = np.where(mask > 0)
    x1, x2 = np.min(xs), np.max(xs)
    y1, y2 = np.min(ys), np.max(ys)
    # noinspection PyUnresolvedReferences
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return cx, cy

# Rotate an image around a center point
def _rotate(img, deg, center):
    h, w, d = img.shape
    cx, cy = center

    matrix = cv2.getRotationMatrix2D((cx, cy), deg, 1)
    rotated = cv2.warpAffine(img, matrix, dsize=(w, h), flags=cv2.INTER_LINEAR)
    return rotated

# Rescale an image from a center point
def _rescale(img, scale, center):
    h, w, d = img.shape
    cx, cy = center

    matrix = np.float32([
        [scale, 0, (1 - scale) * cx],
        [0, scale, (1 - scale) * cy]
    ])
    # dsize=(w, h) ensures the output image is the same size as the original
    scaled = cv2.warpAffine(img, matrix, dsize=(w, h), flags=cv2.INTER_LINEAR)
    return scaled


# For testing only
def _testing_circle_mask(height, width):
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (width // 2, height // 2)
    radius = min(width, height) // 4
    cv2.circle(mask, center, radius, 255, -1)  # White filled circle
    return mask

# For testing only
def _testing_square_mask(height, width):
    mask = np.zeros((height, width), dtype=np.uint8)
    # Define square size (¼ of the smaller image dimension)
    side = min(width, height) // 2
    x1 = (width - side) // 2
    y1 = (height - side) // 2
    x2 = x1 + side
    y2 = y1 + side
    # Draw filled white square in center
    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    return mask

# For testing only
def _testing_offset_square_mask(height, width, offset_x=100, offset_y=50):
    mask = np.zeros((height, width), dtype=np.uint8)
    # Define square size (¼ of smaller dimension)
    side = min(width, height) // 2
    # Start from what would be the center, then apply offset
    x1 = (width - side) // 2 + offset_x
    y1 = (height - side) // 2 + offset_y
    x2 = x1 + side
    y2 = y1 + side
    # Clip to ensure within image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    # Draw filled white square
    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    return mask