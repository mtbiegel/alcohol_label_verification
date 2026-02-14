import cv2
import numpy as np
import re
import pytesseract
from rapidfuzz import fuzz


def preprocess_from_array(img, name):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(gray, h=30)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(binary, -1, kernel)
    morph_kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(sharpened, morph_kernel, iterations=1)
    processed = cv2.erode(processed, morph_kernel, iterations=1)
    name += ".png"
    cv2.imwrite(name, processed)
    return processed


# def preprocess_image(image_path):
#     img = cv2.imread(image_path)
#     processed = preprocess_from_array(img)
#     cv2.imwrite("debug_preprocessed.png", processed)
#     return processed


def find_vertical_split(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    height, width = binary.shape
    col_darkness = []

    for x in range(width):
        col = binary[:, x]
        darkness = np.sum(col == 0) / height  # fraction of dark pixels
        col_darkness.append(darkness)

    # Look for the minimum darkness in the middle third of the image
    mid_start = width // 3
    mid_end = 2 * width // 3
    middle_section = col_darkness[mid_start:mid_end]
    split_col = mid_start + int(np.argmin(middle_section))

    # Only trust the split if the column is mostly empty
    if min(middle_section) < 0.05:
        return split_col
    else:
        return None


def detect_text_regions(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Dilate horizontally to merge text into blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 5))
    dilated = cv2.dilate(binary, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 1000]

    return bounding_boxes


def has_two_column_layout(img):
    """Use bounding boxes as a fallback to check for two-column layout."""
    bounding_boxes = detect_text_regions(img)
    if not bounding_boxes:
        return False

    width = img.shape[1]
    midpoint = width // 2

    left_boxes = [b for b in bounding_boxes if b[0] < midpoint]
    right_boxes = [b for b in bounding_boxes if b[0] >= midpoint]

    return len(left_boxes) > 0 and len(right_boxes) > 0


def split_and_ocr(image_path):
    img = cv2.imread(image_path)

    # First try vertical gap detection
    split_col = find_vertical_split(img)

    if split_col:
        print(f"Two labels detected via vertical gap, splitting at column {split_col}")
        left = img[:, :split_col]
        right = img[:, split_col:]
        cv2.imwrite("debug_left.png", left)
        cv2.imwrite("debug_right.png", right)
        return [
            pytesseract.image_to_string(preprocess_from_array(left, "left")),
            pytesseract.image_to_string(preprocess_from_array(right, "right"))
        ]

    # Fall back to bounding box layout detection
    if has_two_column_layout(img):
        midpoint = img.shape[1] // 2
        print(f"Two labels detected via text regions, splitting at midpoint {midpoint}")
        left = img[:, :midpoint]
        right = img[:, midpoint:]
        cv2.imwrite("debug_left.png", left)
        cv2.imwrite("debug_right.png", right)
        return [
            pytesseract.image_to_string(preprocess_from_array(left, "left")),
            pytesseract.image_to_string(preprocess_from_array(right, "right"))
        ]

    # Single label
    print("Single label detected")
    return [pytesseract.image_to_string(preprocess_from_array(img))]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[''`]', "'", text)
    text = re.sub(r'[–—]', '-', text)
    text = text.replace('0', 'o')
    text = text.replace('1', 'l')
    return text.strip()


def check_government_warning(input_string: str) -> bool:
    GOV_WARNING_STR = "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."

    # Try normalized exact match first
    if normalize(GOV_WARNING_STR) in normalize(input_string):
        return True

    # Fall back to fuzzy match
    score = fuzz.partial_ratio(GOV_WARNING_STR.lower(), input_string.lower())
    print(f"Fuzzy match score: {score}")
    return score >= 95


if __name__ == "__main__":
    path = "/home/mtbiegel/take_home/tests/test_images/3.png"

    labels = split_and_ocr(path)

    for i, label_text in enumerate(labels):
        print(f"\n--- Label {i + 1} ---")
        print(label_text)
        print("Government warning present:", check_government_warning(label_text))