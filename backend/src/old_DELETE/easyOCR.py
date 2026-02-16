import cv2
import numpy as np
import re
import easyocr
from PIL import Image, ImageFilter
from rapidfuzz import fuzz

GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, "
    "women should not drink alcoholic beverages during pregnancy because of the risk of "
    "birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive "
    "a car or operate machinery, and may cause health problems."
)

# Initialize EasyOCR reader once globally (slow to initialize)
print("Loading EasyOCR model...")
reader = easyocr.Reader(['en'], gpu=False)


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_from_array(img: np.ndarray, debug_name: str) -> np.ndarray:
    """Preprocess an image array for OCR. Saves debug image."""

    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Upscale using INTER_LANCZOS4 - better than INTER_CUBIC for text
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)

    # 3. CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 4. Bilateral filter - preserves text edges better than fastNlMeansDenoising
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # 5. Adaptive thresholding - handles uneven lighting across the label better than Otsu
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )

    # 6. Ensure dark text on white background
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)

    # 7. Unsharp mask via Pillow - more controllable sharpening than kernel approach
    pil_img = Image.fromarray(binary)
    sharpened = pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    processed = np.array(sharpened)

    # 8. Light morphological cleanup
    morph_kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(processed, morph_kernel, iterations=1)
    processed = cv2.erode(processed, morph_kernel, iterations=1)

    # Save debug image
    debug_path = f"debug_{debug_name}_preprocessed.png"
    cv2.imwrite(debug_path, processed)
    print(f"  [debug] Saved preprocessed image: {debug_path}")

    return processed


# ── Label Splitting ───────────────────────────────────────────────────────────

def find_vertical_split(img: np.ndarray):
    """Find the column where two side-by-side labels are separated by a gap."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    height, width = binary.shape
    col_darkness = [np.sum(binary[:, x] == 0) / height for x in range(width)]

    mid_start = width // 3
    mid_end = 2 * width // 3
    middle_section = col_darkness[mid_start:mid_end]
    split_col = mid_start + int(np.argmin(middle_section))

    if min(middle_section) < 0.05:
        return split_col
    return None


def has_two_column_layout(img: np.ndarray) -> bool:
    """Fallback: detect two-column layout using text bounding boxes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 5))
    dilated = cv2.dilate(binary, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 1000]

    if not bounding_boxes:
        return False

    midpoint = img.shape[1] // 2
    left_boxes  = [b for b in bounding_boxes if b[0] < midpoint]
    right_boxes = [b for b in bounding_boxes if b[0] >= midpoint]

    return len(left_boxes) > 0 and len(right_boxes) > 0


def split_image(image_path: str) -> list:
    """
    Split image into label regions.
    Returns list of (image_array, label_name) tuples.
    """
    img = cv2.imread(image_path)

    split_col = find_vertical_split(img)
    if split_col:
        print(f"Two labels detected via vertical gap at column {split_col}")
        left  = img[:, :split_col]
        right = img[:, split_col:]
        cv2.imwrite("debug_left_raw.png", left)
        cv2.imwrite("debug_right_raw.png", right)
        print("  [debug] Saved raw split images: debug_left_raw.png, debug_right_raw.png")
        return [(left, "left"), (right, "right")]

    if has_two_column_layout(img):
        midpoint = img.shape[1] // 2
        print(f"Two labels detected via text regions, splitting at midpoint {midpoint}")
        left  = img[:, :midpoint]
        right = img[:, midpoint:]
        cv2.imwrite("debug_left_raw.png", left)
        cv2.imwrite("debug_right_raw.png", right)
        print("  [debug] Saved raw split images: debug_left_raw.png, debug_right_raw.png")
        return [(left, "left"), (right, "right")]

    print("Single label detected")
    return [(img, "single")]


# ── OCR ───────────────────────────────────────────────────────────────────────

def run_ocr(img: np.ndarray, debug_name: str) -> str:
    """Preprocess and run EasyOCR on an image array."""
    processed = preprocess_from_array(img, debug_name)

    # Save the file EasyOCR will read
    temp_path = f"debug_{debug_name}_easyocr_input.png"
    cv2.imwrite(temp_path, processed)
    print(f"  [debug] Saved EasyOCR input image: {temp_path}")

    results = reader.readtext(
        temp_path,
        paragraph=False,
        width_ths=0.9,
        contrast_ths=0.05,
        adjust_contrast=0.7,
        text_threshold=0.5,
        low_text=0.3,
        mag_ratio=1.5
    )

    if not results:
        return ""

    # Sort top to bottom, then left to right within similar vertical positions
    results.sort(key=lambda x: (round(x[0][0][1] / 20) * 20, x[0][0][0]))

    lines = []
    for result in results:
        if len(result) == 3:
            _, text, confidence = result
            if confidence > 0.2:
                lines.append(text)
        else:
            _, text = result
            lines.append(text)

    return "\n".join(lines)


# ── Government Warning Check ──────────────────────────────────────────────────

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[''`]', "'", text)
    text = re.sub(r'[–—]', '-', text)
    text = text.replace('0', 'o')
    text = text.replace('1', 'l')
    return text.strip()


def check_government_warning(text: str) -> tuple:
    """
    Check if the government warning is present in the text.
    Returns (found: bool, fuzzy_score: int).
    """
    # Try normalized exact match first
    if normalize(GOV_WARNING_STR) in normalize(text):
        return True, 100

    # Fall back to fuzzy match
    # Threshold of 85 gives tolerance for typical OCR noise
    score = fuzz.partial_ratio(GOV_WARNING_STR.lower(), text.lower())
    return score >= 85, score


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1.jpg"

    print(f"\nProcessing: {path}")
    print("=" * 60)

    regions = split_image(path)

    gov_warning_found = False

    for img_array, label_name in regions:
        print(f"\n--- Processing {label_name} label ---")
        text = run_ocr(img_array, label_name)

        print(f"\nExtracted text:")
        print("-" * 40)
        print(text)
        print("-" * 40)

        found, score = check_government_warning(text)
        print(f"Government warning present: {found}  (fuzzy score: {score})")

        if found:
            gov_warning_found = True

    print("\n" + "=" * 60)
    print(f"FINAL RESULT - Government warning found: {gov_warning_found}")