import cv2
import numpy as np

def hue_shift(img:np.ndarray, hue:int):
    image = cv2.add(img,  np.array([hue, hue, hue, 0]))  # "add" caps at 255/-255
    return image

# TODO: account for alpha value
def grayscale(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGRA)


def feature_detection(reference_image:np.ndarray, block_size:int, ksize:int, k:float):
    if block_size <= 0:
        return
    if ksize > 31:
        return
    if ksize % 2 == 0:
        return

    gray = cv2.cvtColor(reference_image, cv2.COLOR_BGRA2GRAY)
    gray = np.float32(gray)
    dst = cv2.cornerHarris(gray, block_size, ksize, k)
    #For every value in "dst" that is greater that 1% of the max value in "dst",
    # set the pixel at the equivalent coordinate in "reference_image" to red
    reference_image[dst > 0.01 * dst.max()] = [0, 0, 255, 255]
    return reference_image


# WILL CHANGE SIZE OF IMAGE, NEED IMAGE RESCALING BEFORE USABLE
def add_padding(img, border_type:str, size: tuple[int, int, int, int], color: tuple[int, int, int, int]=None):
    t, b, l, r = size
    if border_type == "replicate":
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_REPLICATE)
    if border_type == "reflect":
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_REFLECT)
    if border_type == "reflect_101":
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_REFLECT_101)
    if border_type == "wrap":
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_WRAP)
    if border_type == "constant" and not (color is None):
        return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_CONSTANT, value=color)
    return img


def sobel_edge(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = cv2.magnitude(sobel_x, sobel_y)
    gradient_magnitude = cv2.convertScaleAbs(gradient_magnitude)
    return cv2.cvtColor(gradient_magnitude, cv2.COLOR_GRAY2BGRA)

def laplace_edge(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian = cv2.convertScaleAbs(laplacian)
    return cv2.cvtColor(laplacian, cv2.COLOR_GRAY2BGRA)

def canny_edge(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    canny = cv2.Canny(gray, threshold1=100, threshold2=200)
    return cv2.cvtColor(canny, cv2.COLOR_GRAY2BGRA)

def gauss_blur(img, ksize: tuple[int, int], sigma_x: float, sigma_y: float = 0):
    if not (ksize[0] > 0 and ksize[0] % 2 == 1 and ksize[1] > 0 and ksize[1] % 2 == 1):
        return img

    return cv2.GaussianBlur(img, ksize, sigmaX=sigma_x, sigmaY=sigma_y)

def median_blur(img, ksize: int):
    if not (ksize > 0 and ksize % 2 == 1):
        return img
    return cv2.medianBlur(img, ksize)

def bilateral_blur(img, d, sigma_color: int, sigma_space: int):
    # Large d values tanks performance and are not that useful anyway
    if d > 10:
        d = 10
    img = cv2.cvtColor(img.copy(), cv2.COLOR_BGRA2BGR)
    img = cv2.bilateralFilter(img, d, sigma_color, sigma_space)
    return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

def kernel_filter(img, kernel:np.ndarray):
    return cv2.filter2D(img, -1, kernel)

def threshold(img, thresh_type:str, thresh:int):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if thresh_type == "binary":
        ret, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "binary_inv":
        ret, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "trunc":
        ret, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_TRUNC)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "tozero":
        ret, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_TOZERO)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "tozero_inv":
        ret, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_TOZERO_INV)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "otsu":
        # Ignores passed thresh
        ret, thresh_img = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    if thresh_type == "triangle":
        # Ignores passed thresh
        ret, thresh_img = cv2.threshold(gray, 0, 255, cv2.THRESH_TRIANGLE)
        return cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGRA)
    return img