import os
import time
import logging
import re
import cv2
import numpy as np
import json

total_start_time = time.perf_counter()

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
logging.disable(logging.WARNING)

from paddleocr import PaddleOCR
from rapidfuzz import fuzz

print("Loading PaddleOCR model...")
ocr = PaddleOCR(
    lang='en',
    device='cpu',
    use_textline_orientation=True,
    use_doc_orientation_classify=True,
    use_doc_unwarping=True
)

GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.")


# ── Text Ordering ─────────────────────────────────────────────────────────────

def get_ordered_text(results, img_width: int, img_height: int) -> list:
    """
    Extract text from PaddleOCR results in correct reading order.
    Groups items into lines by y-proximity, sorts each line left-to-right,
    and handles side-by-side labels by detecting full-height column gaps.
    """
    # 1. Extract all items with bounding box info
    items = []
    for item in results:
        for text, score, poly in zip(item.get('rec_texts', []),
                                     item.get('rec_scores', []),
                                     item.get('dt_polys', [])):
            if score > 0.2 and text.strip():
                items.append({
                    'text':     text,
                    'center_x': np.mean([p[0] for p in poly]),
                    'center_y': np.mean([p[1] for p in poly]),
                    'top_y':    min([p[1] for p in poly]),
                    'bot_y':    max([p[1] for p in poly]),
                    'left_x':   min([p[0] for p in poly]),
                    'right_x':  max([p[0] for p in poly]),
                })

    if not items:
        return []

    # 2. Detect full-height column gap (real label separator spans entire image height)
    num_bands   = 8
    band_height = img_height / num_bands
    mid_start   = img_width // 3
    mid_end     = 2 * img_width // 3
    min_gap_px  = img_width * 0.05

    gap_start  = None
    best_split = None

    for x in range(mid_start, mid_end):
        bands_clear = 0
        for b in range(num_bands):
            band_top = b * band_height
            band_bot = (b + 1) * band_height
            crosses = any(
                i['left_x'] < x < i['right_x'] and
                i['top_y']  < band_bot and
                i['bot_y']  > band_top
                for i in items
            )
            if not crosses:
                bands_clear += 1

        is_clear = (bands_clear / num_bands) >= 0.8

        if is_clear:
            if gap_start is None:
                gap_start = x
        else:
            if gap_start is not None:
                if (x - gap_start) >= min_gap_px:
                    best_split = (gap_start + x) // 2
                    break
            gap_start = None

    # 3. Group items into lines and sort left-to-right within each line
    def sort_into_lines(group: list) -> list:
        if not group:
            return []
        avg_height      = np.mean([i['bot_y'] - i['top_y'] for i in group])
        line_threshold  = avg_height * 0.5
        sorted_items    = sorted(group, key=lambda i: i['center_y'])
        lines           = [[sorted_items[0]]]

        for item in sorted_items[1:]:
            if abs(item['center_y'] - lines[-1][-1]['center_y']) <= line_threshold:
                lines[-1].append(item)
            else:
                lines.append([item])

        result = []
        for line in lines:
            result.extend(sorted(line, key=lambda i: i['left_x']))
        return result

    # 4. Apply to single label or each column
    if best_split is None:
        return [i['text'] for i in sort_into_lines(items)]

    left  = [i for i in items if i['center_x'] <  best_split]
    right = [i for i in items if i['center_x'] >= best_split]

    return [i['text'] for i in sort_into_lines(left)] + \
           [i['text'] for i in sort_into_lines(right)]


# ── Utilities ─────────────────────────────────────────────────────────────────

def read_json_file(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from '{filename}'. Check the file format.")
        return None


def check_government_warning(text_list: list) -> bool:
    all_text = " ".join(text_list)

    if "GOVERNMENT WARNING" not in all_text:
        print("NO WARNING FOUND")
        return False

    start = all_text.find("GOVERNMENT")
    stop  = all_text.find("PROBLEMS.")

    if stop == -1:
        print("WARNING START FOUND BUT NO END (PROBLEMS.) DETECTED")
        return False

    gov_str = all_text[start:stop + len("PROBLEMS.")].upper()

    print("\n")
    print("EXTRACTED:", gov_str)
    print("EXPECTED: ", GOV_WARNING_STR.upper())
    print("-" * 40)

    partial_ratio = fuzz.partial_ratio(gov_str, GOV_WARNING_STR.upper())
    print("PARTIAL RATIO:", partial_ratio)

    if partial_ratio == 100:
        print("EXACT MATCH")
        return True
    elif partial_ratio >= 95:
        print("PARTIAL MATCH - NEEDS MANUAL REVIEW:", partial_ratio)
        return False
    else:
        print("NOT A MATCH:", partial_ratio)
        return False


# ── Main Processing ───────────────────────────────────────────────────────────

image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/9.png"
json_path  = "/home/biegemt1/projects/alcohol_label_verification/tests/applications/9.json"

print(f"\nProcessing: {image_path}")
print("=" * 60)

data = read_json_file(json_path)
img  = cv2.imread(image_path)

start_time = time.perf_counter()
results    = ocr.predict(img)
stop_time  = time.perf_counter()

# Get text in correct reading order
text_result_list = get_ordered_text(results, img.shape[1], img.shape[0])
print("\nOrdered Output:", text_result_list)

correct_gov_warning = check_government_warning(text_result_list)

for item in data:
    data[item] = data[item].strip().replace(" ", "")
    print("Data item:", data[item])

all_words_no_spaces = "".join(text_result_list).split("GOVERNMENT")[0]
print("all_words_no_spaces:", all_words_no_spaces)

if data["brand_name"][0] in all_words_no_spaces:
    print("brand_name is THERE")

if correct_gov_warning:
    print("LABEL PASSES")
else:
    print("LABEL FAILS")

total_stop_time = time.perf_counter()

# TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model)
# NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least

elapsed_time = stop_time - start_time
total_time   = total_stop_time - total_start_time
print("\nOCR time:", elapsed_time)
print("Total script time:", total_time)