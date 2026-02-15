import os
import time
import logging
import cv2
import numpy as np

total_start_time = time.perf_counter()

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
logging.disable(logging.WARNING)

from paddleocr import PaddleOCR

# Updated API for newer versions of PaddleOCR:
# - use_textline_orientation replaces use_angle_cls
# - device='cpu' replaces use_gpu=False
print("Loading PaddleOCR model...")
ocr = PaddleOCR(
    lang='en',
    device='cpu',
    use_textline_orientation=True,
    use_doc_orientation_classify=True,  # False to speed up
    use_doc_unwarping=True              # False to speed up
    # text_det_limit_side_len=960
)


# ── Vertical Splitting ────────────────────────────────────────────────────────

def find_vertical_split(img):
    """
    Find the column where two side-by-side labels are separated by a gap.
    Only looks in the middle third of the image to avoid edge false positives.
    Returns the split column index, or None if no clear gap found.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    height, width = binary.shape
    col_darkness = [np.sum(binary[:, x] == 0) / height for x in range(width)]

    mid_start = width // 3
    mid_end = 2 * width // 3
    middle_section = col_darkness[mid_start:mid_end]
    split_col = mid_start + int(np.argmin(middle_section))

    # Only accept if the column is mostly empty (< 5% dark pixels)
    if min(middle_section) < 0.05:
        return split_col
    return None


def has_two_column_layout(img):
    """
    Fallback: detect two-column layout using text bounding boxes.
    Returns True if significant text regions exist on both left and right halves.
    """
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


def split_image(img):
    """
    Detect and split image into left/right regions if multiple labels present.
    PaddleOCR reads top-to-bottom naturally so only vertical splitting is needed.
    Returns list of (image_array, label_name) tuples.
    """
    # Try gap-based split first (most reliable)
    split_col = find_vertical_split(img)
    if split_col:
        print(f"Two labels detected via gap, splitting at column {split_col}")
        # left  = img[:, :split_col]
        # right = img[:, split_col:]
        # cv2.imwrite("debug_left_raw.png", left)
        # cv2.imwrite("debug_right_raw.png", right)
        # return [(left, "left"), (right, "right")]
        return True

    # Fallback: bounding box layout detection
    if has_two_column_layout(img):
        print(f"Two labels detected via text regions, splitting at midpoint {midpoint}")
        return True

    print("Single label detected")
    return False


def get_ordered_text(results, img_width):
    """
    Run OCR once on the full image and use bounding box x-coordinates
    to separate left/right labels, then sort each top-to-bottom.
    """
    all_items = []

    for item in results:
        rec_texts = item.get('rec_texts', [])
        rec_scores = item.get('rec_scores', [])
        dt_polys = item.get('dt_polys', [])  # Bounding box coordinates

        for text, score, poly in zip(rec_texts, rec_scores, dt_polys):
            if score > 0.2:
                # Get center x and top y of the bounding box
                center_x = np.mean([p[0] for p in poly])
                top_y    = min([p[1] for p in poly])
                all_items.append((center_x, top_y, text))

    # Find the natural split point - large gap in x-coordinates
    x_coords = sorted([item[0] for item in all_items])
    split_x = img_width // 2  # Default to midpoint

    if len(x_coords) > 1:
        gaps = [(x_coords[i+1] - x_coords[i], i) for i in range(len(x_coords)-1)]
        largest_gap = max(gaps, key=lambda g: g[0])
        if largest_gap[0] > img_width * 0.1:  # Gap must be > 10% of image width
            split_x = (x_coords[largest_gap[1]] + x_coords[largest_gap[1]+1]) / 2

    # Separate into left/right and sort each top-to-bottom
    left_items  = sorted([i for i in all_items if i[0] < split_x],  key=lambda i: i[1])
    right_items = sorted([i for i in all_items if i[0] >= split_x], key=lambda i: i[1])

    left_text  = "\n".join([i[2] for i in left_items])
    right_text = "\n".join([i[2] for i in right_items])

    return left_text, right_text, len(right_items) > 0  # third value = was split detected

# ── Main Processing ───────────────────────────────────────────────────────────

# Path to your test image
image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/2.png"
print(f"\nProcessing: {image_path}")
print("=" * 60)

img = cv2.imread(image_path)
start_time = time.perf_counter()
results = ocr.predict(img)  # One OCR pass only
stop_time = time.perf_counter()

if (split_image(img)):
    print("SPLIT LABEL")
    left_text, right_text, was_split = get_ordered_text(results, img.shape[1])
    print("LEFT LABEL:\n", left_text)
    print("RIGHT LABEL:\n", right_text)

else:
    print("SINGLE LABEL")
    for item in results:
        for field in item:
            if field.strip() == "rec_texts":
                print(item[field])



# TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model)
# TODO: Need to clean output array
# NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least

elapsed_time = stop_time - start_time
print("Elapsed time:", elapsed_time)