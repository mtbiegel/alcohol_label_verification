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

print("Loading PaddleOCR model...")
ocr = PaddleOCR(
    lang='en',
    device='cpu',
    use_textline_orientation=True,
    use_doc_orientation_classify=True,  # False to speed up
    use_doc_unwarping=True              # False to speed up
)


# ── Text Ordering ─────────────────────────────────────────────────────────────

def get_ordered_text(results, img_width):
    """
    Use bounding box x-coordinates to separate left/right label text,
    then sort each group top-to-bottom.
    Runs on a single OCR pass — no image splitting needed.
    """
    all_items = []

    for item in results:
        rec_texts  = item.get('rec_texts', [])
        rec_scores = item.get('rec_scores', [])
        dt_polys   = item.get('dt_polys', [])

        for text, score, poly in zip(rec_texts, rec_scores, dt_polys):
            if score > 0.2 and text.strip():
                center_x = np.mean([p[0] for p in poly])
                top_y    = min([p[1] for p in poly])
                all_items.append((center_x, top_y, text))

    if not all_items:
        return "", "", False

    # Find the natural split point using largest x-coordinate gap
    x_coords = sorted([item[0] for item in all_items])
    split_x = img_width // 2  # Default to midpoint

    if len(x_coords) > 1:
        gaps = [(x_coords[i+1] - x_coords[i], i) for i in range(len(x_coords) - 1)]
        largest_gap = max(gaps, key=lambda g: g[0])
        if largest_gap[0] > img_width * 0.1:  # Gap must be > 10% of image width
            split_x = (x_coords[largest_gap[1]] + x_coords[largest_gap[1] + 1]) / 2

    # Separate into left/right and sort each group top-to-bottom
    left_items  = sorted([i for i in all_items if i[0] <  split_x], key=lambda i: i[1])
    right_items = sorted([i for i in all_items if i[0] >= split_x], key=lambda i: i[1])

    left_text  = "\n".join([i[2] for i in left_items])
    right_text = "\n".join([i[2] for i in right_items])

    was_split = len(left_items) > 0 and len(right_items) > 0

    return left_text, right_text, was_split


# ── Main Processing ───────────────────────────────────────────────────────────

image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/2.png"
print(f"\nProcessing: {image_path}")
print("=" * 60)

img = cv2.imread(image_path)

start_time = time.perf_counter()
results = ocr.predict(img)
stop_time = time.perf_counter()

left_text, right_text, was_split = get_ordered_text(results, img.shape[1])

if was_split:
    print("SPLIT LABEL DETECTED")
    print("\nLEFT LABEL:")
    print("-" * 40)
    print(left_text)
    print("\nRIGHT LABEL:")
    print("-" * 40)
    print(right_text)
else:
    print("SINGLE LABEL DETECTED")
    print("-" * 40)
    print(left_text)

# TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model)
# TODO: Need to clean output array
# NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least

elapsed_time = stop_time - start_time
total_time = stop_time - total_start_time
print("\nOCR time:", elapsed_time)
print("Total script time:", total_time)