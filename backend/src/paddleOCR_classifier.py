import os
import time
import logging
import re
import cv2
import numpy as np

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
    use_doc_orientation_classify=True,  # False to speed up
    use_doc_unwarping=True              # False to speed up
)

GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.")

ALCOHOL_TYPES = [
    "beer", "ale", "lager", "stout", "porter", "ipa", "pilsner", "saison",
    "wheat", "sour", "cider", "mead", "wine", "red wine", "white wine",
    "rose", "sparkling", "champagne", "whiskey", "whisky", "bourbon",
    "scotch", "rye", "vodka", "gin", "rum", "tequila", "mezcal",
    "brandy", "cognac", "liqueur", "hard seltzer", "hard cider",
    "pale ale", "amber ale", "brown ale", "blonde ale", "craft"
]


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
    split_x = img_width // 2

    if len(x_coords) > 1:
        gaps = [(x_coords[i+1] - x_coords[i], i) for i in range(len(x_coords) - 1)]
        largest_gap = max(gaps, key=lambda g: g[0])
        if largest_gap[0] > img_width * 0.1:
            split_x = (x_coords[largest_gap[1]] + x_coords[largest_gap[1] + 1]) / 2

    left_items  = sorted([i for i in all_items if i[0] <  split_x], key=lambda i: i[1])
    right_items = sorted([i for i in all_items if i[0] >= split_x], key=lambda i: i[1])

    left_text  = "\n".join([i[2] for i in left_items])
    right_text = "\n".join([i[2] for i in right_items])

    was_split = len(left_items) > 0 and len(right_items) > 0

    return left_text, right_text, was_split


# ── Classification ────────────────────────────────────────────────────────────

def classify_label(left_text: str, right_text: str, was_split: bool) -> dict:
    """
    Extract structured fields from OCR text.
    For split labels, brand/type/ABV/net contents are typically on the front (left)
    and the government warning is typically on the back (right).
    """
    # Combine all text for fields that could appear on either side
    full_text = left_text + "\n" + right_text
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    front_lines = [l.strip() for l in left_text.splitlines() if l.strip()]

    return {
        "brand_name":         extract_brand_name(front_lines, lines),
        "alcohol_type":       extract_alcohol_type(full_text),
        "abv":                extract_abv(full_text),
        "net_contents":       extract_net_contents(full_text),
        "government_warning": check_government_warning(full_text),
    }


def extract_brand_name(front_lines: list, all_lines: list) -> str:
    """
    Brand name is typically the largest/first text on the front label.
    Use the first 1-3 lines of the front label as the candidate.
    Skip very short lines or lines that look like descriptors.
    """
    skip_patterns = [
        r'^\d+', r'%', r'oz', r'ml', r'pint', r'fl\.', r'alc',
        r'brewed', r'bottled', r'canned', r'distilled', r'product',
        r'warning', r'government'
    ]

    lines_to_check = front_lines if front_lines else all_lines

    for line in lines_to_check[:5]:  # Check first 5 lines
        lower = line.lower()
        if len(line) < 2:
            continue
        if any(re.search(p, lower) for p in skip_patterns):
            continue
        return line

    return "Not found"


def extract_alcohol_type(text: str) -> str:
    """Match against known alcohol type keywords."""
    lower = text.lower()
    for alcohol_type in ALCOHOL_TYPES:
        if alcohol_type in lower:
            return alcohol_type.title()
    return "Not found"


def extract_abv(text: str) -> str:
    """
    Extract ABV percentage. Handles formats like:
    5% ALC/VOL, Alcohol 5% By Volume, 5% ABV, ALC. 5% BY VOL
    """
    patterns = [
        r'(\d+(?:\.\d+)?)\s*%\s*(?:alc(?:ohol)?(?:\.)?(?:/vol)?(?:\s*by\s*vol(?:ume)?)?)',
        r'(?:alc(?:ohol)?(?:\.)?(?:/vol)?(?:\s*by\s*vol(?:ume)?)?)\s*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%\s*abv',
        r'(\d+(?:\.\d+)?)\s*%',  # Fallback: any percentage
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}%"
    return "Not found"


def extract_net_contents(text: str) -> str:
    """
    Extract net contents/volume. Handles formats like:
    355 mL, 12 FL OZ, 1 PINT, 750ml, 1 PINT 0.9 FL. OZ.
    """
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz\.?)',
        r'(\d+(?:\.\d+)?)\s*(?:ml|milliliters?)',
        r'(\d+(?:\.\d+)?)\s*(?:l|liters?)\b',
        r'(\d+(?:\.\d+)?)\s*(?:pints?)',
        r'(\d+(?:\.\d+)?)\s*(?:gallons?)',
    ]
    found = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found.append(match.group(0).strip())
    return ", ".join(found) if found else "Not found"


def check_government_warning(text: str) -> dict:
  
    text_split = text.split('\n')

    print("text_split:", text_split)
    print("-------------------")
    
    start = 0
    stop = 0

    if ("GOVERNMENT WARNING" in text):
        for i in range(len(text_split)):
            print("text:", text_split[i])
            if "GOVERNMENT" in text_split[i]:
                print("GOV", i, ":", text_split[i])
                start = i
            if "PROBLEMS." in text_split[i]:
                print("PROBLEMS" , i , ":", text_split[i])
                stop = i
            
            
        gov_str = " ".join(text_split[start:stop+1])
    
        print("\n\n")
        print(gov_str.upper())
        print(GOV_WARNING_STR.upper())
        print("-------------------")

        if (gov_str.upper() == GOV_WARNING_STR.upper()):
            print("EXACT MATCH")
        else:
            print("NOT EXACT MATCH")
    else:
        print("NO WARNING FOUND")
        return {"present": False, "exact_match": False}

    # Need to use fuzzy to determine if it's close but not perfect (aka manual review)
    return {"present": False, "exact_match": False}


# ── Main Processing ───────────────────────────────────────────────────────────

image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/7.png"
print(f"\nProcessing: {image_path}")
print("=" * 60)

img = cv2.imread(image_path)

start_time = time.perf_counter()
results = ocr.predict(img)
stop_time = time.perf_counter()

left_text, right_text, was_split = get_ordered_text(results, img.shape[1])

# Print raw ordered text
# if was_split:
#     print("SPLIT LABEL DETECTED")
#     print("\nLEFT LABEL:")
#     print("-" * 40)
#     print(left_text)
#     print("\nRIGHT LABEL:")
#     print("-" * 40)
#     print(right_text)
# else:
#     print("SINGLE LABEL DETECTED")
#     print("-" * 40)
#     print(left_text)

# Print classified fields
print("\n" + "=" * 60)
print("CLASSIFIED FIELDS:")
print("=" * 60)

fields = classify_label(left_text, right_text, was_split)

print(f"Brand Name:         {fields['brand_name']}")
print(f"Alcohol Type:       {fields['alcohol_type']}")
print(f"ABV:                {fields['abv']}")
print(f"Net Contents:       {fields['net_contents']}")
print(f"Government Warning: {fields['government_warning']['present']}")

# TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model)
# NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least

elapsed_time = stop_time - start_time
total_time = stop_time - total_start_time
print("\nOCR time:", elapsed_time)
print("Total script time:", total_time)

print("HERE")
for item in results:
    for field in item:
        print(field)
        if field == "rec_texts":
            print("\n\n",item[field])
            