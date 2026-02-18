import os
import time
import logging
import re
import cv2
from cv2 import dnn_superres
import numpy as np
import json
import time

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
logging.disable(logging.WARNING)

from paddleocr import PaddleOCR
from rapidfuzz import fuzz

# Gov warning string
GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.")

# Spirit type vocabulary
SPIRIT_TYPES = [
    # Whiskies
    'whisky', 'whiskey', 'bourbon', 'rye', 'scotch', 'malt',
    
    # White Spirits
    'vodka', 'gin', 'tequila', 'mezcal', 'rum', 
    'cachaca', 'pisco', 'soju', 'baijiu', 'shochu',
    
    # Brandies
    'brandy', 'cognac', 'armagnac', 'calvados', 'grappa',
    
    # Liqueurs & Cordials
    'liqueur', 'cordial', 'amaretto', 'schnapps', 
    'sambuca', 'chartreuse', 'benedictine', 'drambuie',
    'triple sec', 'curacao', 'limoncello',
    
    # Fortified Wines
    'vermouth', 'sherry', 'port', 'madeira', 'marsala',
    
    # Other Spirits
    'absinthe', 'aquavit', 'ouzo', 'arak', 'pastis', 'sake',
    
    # Beer (TTB regulates beer too)
    'beer', 'ale', 'lager', 'stout', 'porter', 'pilsner',
    'ipa', 'wheat beer', 'hefeweizen', 'saison', 'lambic',
    
    # Wine
    'wine', 'champagne', 'cider', 'mead'
]

# Descriptors that precede a spirit type
SPIRIT_DESCRIPTORS = [
    'straight', 'single', 'barrel', 'double', 'aged', 'small',
    'batch', 'blended', 'pure', 'premium', 'rare', 'reserve',
    'select', 'special', 'cask', 'strength', 'malt', 'grain',
    'kentucky', 'tennessee', 'irish', 'japanese', 'canadian',
    'american', 'extra', 'anejo', 'reposado', 'blanco'
]

# Words that are definitely NOT the brand name
NOT_BRAND_WORDS = [
    'distilled', 'bottled', 'produced', 'imported', 'brewed',
    'by:', 'by', 'and', 'the', 'of', 'a', 'an',
    'government', 'warning', 'according', 'surgeon', 'general',
    'net', 'contents', 'alcohol', 'alc', 'vol', 'proof',
    'ml', 'l', 'oz', 'liter', 'litre',
    *SPIRIT_TYPES,
    *SPIRIT_DESCRIPTORS
]

def preprocess_image_for_ocr(img):
    """Improve image quality for OCR"""
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Increase contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast = clahe.apply(denoised)
    
    # Sharpen
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    sharpened = cv2.filter2D(contrast, -1, kernel)
    
    # Threshold to clean binary image
    _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to BGR for PaddleOCR
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

def sort_text(results, img_width: int, img_height: int) -> tuple[list, int | None]:
    """
    Extract text from PaddleOCR results in correct reading order.
    Groups items into lines by y-proximity, sorts each line left-to-right,
    and handles side-by-side labels by detecting full-height column gaps.
    Returns (sorted_text_list, best_split_x)
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
        return [], None

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

    # 4. Apply to single label or each column  ← THIS IS UNCHANGED, splitting still happens
    if best_split is None:
        return [i['text'] for i in sort_into_lines(items)], None  # ← only change

    left  = [i for i in items if i['center_x'] <  best_split]
    right = [i for i in items if i['center_x'] >= best_split]

    return [i['text'] for i in sort_into_lines(left)] + \
           [i['text'] for i in sort_into_lines(right)], best_split  # ← only change

def process_image_ocr(model, img):
    return model.predict(img)

def load_model():
    # Load in model
    print("Loading PaddleOCR model...")
    ocr = PaddleOCR(
        lang='en',
        device='cpu',
        use_textline_orientation=True,
        use_doc_orientation_classify=True,
        use_doc_unwarping=True,
    )

    return ocr

def check_government_warning(text_list: list) -> tuple[str, str | None]:
    """
    Checks the government warning statement against the required text.
    
    Returns:
        ('pass', None)                  - exact match
        ('warning', note)               - close but not exact, needs review
        ('fail', note)                  - missing or too different
    """
    all_text = " ".join(text_list).upper()
    expected = GOV_WARNING_STR.upper()

    # ── Step 1: Check if warning is present at all ──
    if "GOVERNMENT WARNING" not in all_text:
        return ('fail', 'Government warning statement not found on label')

    # ── Step 2: Check if "GOVERNMENT WARNING:" is correctly capitalized ──
    # Since we already uppercased everything, check the original text_list
    original_text = " ".join(text_list)
    if "GOVERNMENT WARNING:" not in original_text:
        if "government warning:" in original_text.lower():
            # Present but not in all caps - this is a specific TTB violation
            return ('fail', '"GOVERNMENT WARNING:" must be in all capitals')

    # ── Step 3: Extract just the warning portion from the label ──
    start_word = "GOVERNMENT"
    end_word   = "PROBLEMS."

    start = all_text.find(start_word)
    end   = all_text.find(end_word)

    if start == -1:
        return ('fail', 'Government warning statement not found on label')

    if end == -1:
        # Warning starts but doesn't end — truncated or cut off
        extracted_warning = all_text[start:].strip()
        return ('warning', 'Warning statement appears truncated — could not find end of statement')

    extracted_warning = all_text[start : end + len(end_word)].strip()

    # ── Step 4: Exact match ──
    if extracted_warning == expected:
        return ('pass', None)

    # ── Step 5: Fuzzy match for close but not exact ──
    full_ratio    = fuzz.ratio(extracted_warning, expected)
    partial_ratio = fuzz.partial_ratio(extracted_warning, expected)
    best_score    = max(full_ratio, partial_ratio)
    best_score_rounded = round(best_score, 1)

    # Exact match threshold
    if best_score == 100:
        return ('pass', None)

    # Close enough to be a likely OCR error rather than intentional change
    if best_score >= 95:
        return ('warning', f'Warning statement is very close but not exact (similarity: {best_score_rounded}%). May be an OCR artifact — manual review recommended')

    # Recognizable but has meaningful differences
    if best_score >= 80:
        return ('warning', f'Warning statement has notable differences from required text (similarity: {best_score_rounded}%). Manual review required')

    # Present but too different — likely wrong or heavily modified
    return ('fail', f'Warning statement does not match required text (similarity: {best_score_rounded}%)')

def classify_brand_name(text_list: list, ocr_results: list, best_split: int | None = None) -> str:
    candidates = []
    for item in ocr_results:
        for text, score, poly in zip(
            item.get('rec_texts', []),
            item.get('rec_scores', []),
            item.get('dt_polys', [])
        ):
            if score < 0.5 or not text.strip():
                continue

            text_lower = text.strip().lower()
            if text_lower in NOT_BRAND_WORDS:
                continue
            if text.isdigit() or len(text.strip()) < 2:
                continue
            if re.search(r'\d+%|\d+\s*ml|\d+\s*l\b', text_lower):
                continue

            y_coords = [p[1] for p in poly]
            x_coords = [p[0] for p in poly]

            candidates.append({
                'text':    text.strip(),
                'height':  max(y_coords) - min(y_coords),
                'y':       np.mean(y_coords),
                'x':       np.mean(x_coords),
                'left_x':  min(x_coords),
                'right_x': max(x_coords),
                'score':   score
            })

    if not candidates:
        return ""

    # Filter to top 50% of label
    all_y = [c['y'] for c in candidates]
    img_height_approx = max(all_y) + 50
    top_candidates = [c for c in candidates if c['y'] < img_height_approx * 0.5]

    if not top_candidates:
        top_candidates = candidates

    # Find tallest token
    tallest = max(top_candidates, key=lambda c: c['height'])

    # ── Constrain to same column using best_split ──
    if best_split is not None:
        tallest_side = 'left' if tallest['x'] < best_split else 'right'
        top_candidates = [
            c for c in top_candidates
            if ('left' if c['x'] < best_split else 'right') == tallest_side
        ]

    # Group tokens on the same line
    line_threshold = tallest['height'] * 0.5
    same_line = [
        c for c in top_candidates
        if abs(c['y'] - tallest['y']) <= line_threshold
        and c['text'].lower() not in NOT_BRAND_WORDS
    ]

    if not same_line:
        return tallest['text']

    same_line_sorted = sorted(same_line, key=lambda c: c['left_x'])
    return ' '.join(c['text'] for c in same_line_sorted)

def classify_class_type(text_list: list) -> str:
    """
    Extract class/type by finding spirit keywords and collecting their descriptors.
    e.g., 'STRAIGHT RYE WHISKY' or 'SINGLE BARREL KENTUCKY BOURBON'
    """
    text_lower_list = [t.lower().strip() for t in text_list]

    print()
    print("HERE:")
    print(text_lower_list)
    print()

    # Find all spirit keyword positions
    # spirit_positions = [
    #     i for i, t in enumerate(text_lower_list)
    #     if t in SPIRIT_TYPES
    # ]
    spirit_positions = []
    for i in range(len(text_lower_list)):
        if text_lower_list[i] in SPIRIT_TYPES:
            spirit_positions.append(i)

    print('test1')
    if not spirit_positions:
        print("IN HEREEEEEEEEEE")
        return ""
    # For each spirit keyword found, collect surrounding context
    # Take the one with the most descriptor context (most complete type string)
    best_result = ""

    print("SPIRIT POS:", spirit_positions)
    for spirit_idx in spirit_positions:
        print("FOR LOOP")
        parts = []

        # Look back up to 4 words for descriptors
        lookback = min(4, spirit_idx)
        for i in range(spirit_idx - lookback, spirit_idx):
            word = text_list[i].strip()
            if word.lower() in SPIRIT_DESCRIPTORS or word.lower() in SPIRIT_TYPES:
                parts.append(word)
            else:
                # Reset if we hit a non-descriptor — don't want to grab brand name
                parts = []

        # Add the spirit word itself
        parts.append(text_list[spirit_idx].strip())

        # Look ahead 1 word in case of "WHISKY DISTILLED" etc.
        if spirit_idx + 1 < len(text_list):
            next_word = text_list[spirit_idx + 1].strip()
            if next_word.lower() in SPIRIT_TYPES or next_word.lower() in SPIRIT_DESCRIPTORS:
                parts.append(next_word)

        candidate = ' '.join(parts)

        # Keep the most descriptive result
        if len(candidate) > len(best_result):
            print("IN IF")
            best_result = candidate
        else:
            print("IN ELSE")
    
    print("BESTTTTTTTTTTT:", best_result)
    return best_result

def classify_alcohol_content(text_list: list) -> str:
    """
    Extract alcohol content using regex patterns.
    Handles formats like: '45% ALC/VOL', '45% Alc./Vol.', '90 PROOF', '45%'
    Reconstructs value if split across multiple OCR tokens.
    """
    # Join list preserving spaces for regex
    full_text = ' '.join(text_list)

    patterns = [
        # Most complete: percentage + ALC/VOL
        r'\d+\.?\d*\s*%\s*(?:ALC\.?/?VOL\.?|ABV)',
        # Percentage + PROOF
        r'\d+\.?\d*\s*(?:PROOF)',
        # Bare percentage (last resort)
        r'\d+\.?\d*\s*%',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            result = match.group(0).strip()

            # Try to extend match to grab PROOF if adjacent
            # e.g., "45% ALC/VOL (90 PROOF)"
            extended_pattern = r'\d+\.?\d*\s*%\s*(?:ALC\.?/?VOL\.?)?\s*\(?\d+\.?\d*\s*PROOF\)?'
            ext_match = re.search(extended_pattern, full_text, re.IGNORECASE)
            if ext_match:
                return ext_match.group(0).strip()

            return result

    # Fallback: check individual tokens for split values like ["45%", "ALC/VOL"]
    for i, text in enumerate(text_list):
        if re.match(r'^\d+\.?\d*%$', text.strip()):
            # Check next token for ALC/VOL
            if i + 1 < len(text_list):
                next_token = text_list[i + 1].strip()
                if re.match(r'^(?:ALC\.?/?VOL\.?|ABV|PROOF)$', next_token, re.IGNORECASE):
                    return f"{text.strip()} {next_token}"
            return text.strip()

    return ""

def classify_net_contents(text_list: list) -> str:
    """
    Extract net contents (volume).
    Handles: '750 ML', '750ML', '1 L', '1.75L', '750 mL'
    Reconstructs value if split across tokens.
    """
    full_text = ' '.join(text_list)

    patterns = [
        r'\d+\.?\d*\s*(?:ML|mL|cl|CL|litre|liter|LITER|LITRE)\b',
        r'\d+\.?\d*\s*L\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    # Fallback: look for split tokens like ["750", "ML"]
    for i, text in enumerate(text_list):
        if re.match(r'^\d+\.?\d*$', text.strip()):
            if i + 1 < len(text_list):
                next_token = text_list[i + 1].strip()
                if re.match(r'^(?:ML|mL|L|cl|CL|litre|liter)$', next_token, re.IGNORECASE):
                    return f"{text.strip()} {next_token}"

    return ""

def verify_label(model, image_bytes, application_data):

    # Load in label image from bytes
    np_img_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_img_arr, cv2.IMREAD_COLOR)

    img = preprocess_image_for_ocr(img)

    # Run paddleOCR
    results = process_image_ocr(model, img)

    # Sort output from paddleOCR so text is in reading order
    text_result_list, best_split = sort_text(results, img.shape[1], img.shape[0])

    print("=" * 60)
    print("RAW OCR OUTPUT:")
    print("=" * 60)
    for i, text in enumerate(text_result_list):
        print(f"[{i:02d}] {text}")
    print("=" * 60)

    # ── Run classifiers ──
    extracted_brand = classify_brand_name(text_result_list, results, best_split)
    extracted_class = classify_class_type(text_result_list)
    extracted_alcohol = classify_alcohol_content(text_result_list)
    extracted_contents = classify_net_contents(text_result_list)
    has_valid_warning = check_government_warning(text_result_list)

    def compare_brand_name(extracted: str, expected: str) -> tuple:
        if not extracted:
            return ('fail', 'Brand name not found on label')
        if not expected:
            return ('pass', None)

        ext_norm = extracted.lower().strip()
        exp_norm = expected.lower().strip()

        # Exact match
        if ext_norm == exp_norm:
            return ('pass', None)

        # Length difference check — must be within 85% of each other
        # "AB" vs "ABC" = 0.67 → fail
        # "ABCD" vs "ABC" = 0.75 → fail
        # "ABCE" vs "ABCD" = 1.0 → proceed to fuzzy
        len_ratio = min(len(ext_norm), len(exp_norm)) / max(len(ext_norm), len(exp_norm))
        if len_ratio < 0.85:
            return ('fail', f'Brand name mismatch: found "{extracted}", expected "{expected}"')

        # Only use fuzz.ratio — never partial_ratio for brand names
        # partial_ratio causes false positives by matching substrings
        similarity = fuzz.ratio(ext_norm, exp_norm)
        similarity_rounded = round(similarity, 1)

        if similarity == 100:
            return ('pass', None)

        # High similarity — likely just case or minor OCR difference
        if similarity >= 90:
            return ('warning', f'Minor difference (similarity {similarity_rounded}%)')

        # Moderate similarity — possibly correct but needs review
        if similarity >= 75:
            return ('warning', f'Possible match but significant difference( similarity {similarity_rounded}%)')

        return ('fail', f'Brand name mismatch')

    def compare_class_type(extracted: str, expected: str) -> tuple:
        if not extracted:
            return ('fail', 'Class/type not found on label')
        if not expected:
            return ('pass', None)

        ext_norm = extracted.lower().strip()
        exp_norm = expected.lower().strip()

        # Exact match
        if ext_norm == exp_norm:
            return ('pass', None)

        # One is a substring of the other
        if ext_norm in exp_norm or exp_norm in ext_norm:
            return ('warning', f'Partial match — verify full class/type on label')

        # Fuzzy match for things like "Whiskey" vs "Whisky"
        similarity = fuzz.ratio(ext_norm, exp_norm)
        partial    = fuzz.partial_ratio(ext_norm, exp_norm)
        best       = max(similarity, partial)
        best_rounded = round(best, 1)

        if best >= 80:
            return ('warning', f'Close match but difference detected (similarity: {best_rounded}%)"')

        return ('fail', f'Class/type mismatch')

    def compare_alcohol_content(extracted: str, expected: str) -> tuple:
        """
        Compare alcohol content flexibly.
        '47% ABV', '47% ALC/VOL', '47%', '47 PROOF' should all match if the number matches.
        """
        if not extracted:
            return ('fail', 'Alcohol content not found on label')
        if not expected:
            return ('pass', None)

        # Pull the number out of both strings
        ext_nums = re.findall(r'\d+\.?\d*', extracted)
        exp_nums = re.findall(r'\d+\.?\d*', expected)

        if not ext_nums or not exp_nums:
            return ('fail', f'Could not parse alcohol content: "{extracted}" vs "{expected}"')

        ext_num = float(ext_nums[0])
        exp_num = float(exp_nums[0])

        # Numbers match exactly
        if ext_num == exp_num:
            # Check if format indicators are compatible (ABV vs ALC/VOL is fine, PROOF vs % is a warning)
            ext_has_proof = 'proof' in extracted.lower()
            exp_has_proof = 'proof' in expected.lower()

            if ext_has_proof != exp_has_proof:
                return ('warning', f'Percentage matches but format differs"')

            return ('pass', None)

        # Numbers are close but not exact (rounding differences)
        if abs(ext_num - exp_num) <= 0.5:
            return ('warning', f'Minor difference detected"')

        return ('fail', f'Alcohol content mismatch')

    def compare_net_contents(extracted: str, expected: str) -> tuple:
        """
        Compare net contents with explicit combined string e.g. '750 mL'.
        Number AND unit must both match to pass.
        """
        if not extracted:
            return ('fail', 'Net contents not found on label')
        if not expected:
            return ('pass', None)

        # Pull number from both
        ext_nums = re.findall(r'\d+\.?\d*', extracted)
        exp_nums = re.findall(r'\d+\.?\d*', expected)

        if not ext_nums or not exp_nums:
            return ('fail', f'Could not parse net contents: "{extracted}" vs "{expected}"')

        # Numbers must match
        if ext_nums[0] != exp_nums[0]:
            return ('fail', f'Volume mismatch: found "{extracted}", expected "{expected}"')

        # Unit must match
        ext_unit = re.sub(r'[\d\.\s]', '', extracted).strip().lower()
        exp_unit = re.sub(r'[\d\.\s]', '', expected).strip().lower()

        if ext_unit != exp_unit:
            return ('fail', f'Unit mismatch: found "{extracted}", expected "{expected}"')

        return ('pass', None)

    brand_status, brand_note = compare_brand_name(extracted_brand, application_data.get('brand_name', ''))
    class_status, class_note = compare_class_type(extracted_class, application_data.get('class_type', ''))
    alcohol_status, alcohol_note = compare_alcohol_content(extracted_alcohol, application_data.get('alcohol_content', ''))
    contents_status, contents_note = compare_net_contents(extracted_contents, f"{application_data['net_contents_amount']} {application_data['net_contents_unit']}")
    warning_status, warning_note = check_government_warning(text_result_list)

    # ── Build response ──
    fields = [
        {
            'field':     'Brand Name',
            'extracted': extracted_brand,
            'expected':  application_data.get('brand_name', ''),
            'status':    brand_status,
            'note':      brand_note
        },
        {
            'field':     'Class/Type',
            'extracted': extracted_class,
            'expected':  application_data.get('class_type', ''),
            'status':    class_status,
            'note':      class_note
        },
        {
            'field':     'Alcohol Content',
            'extracted': extracted_alcohol,
            'expected':  application_data.get('alcohol_content', ''),
            'status':    alcohol_status,
            'note':      alcohol_note
        },
        {
            'field':     'Net Contents',
            'extracted': extracted_contents,
            'expected':  application_data.get('net_contents', ''),
            'status':    contents_status,
            'note':      contents_note
        },
        {
            'field':     'Government Warning',
            'extracted': 'GOVERNMENT WARNING: present' if has_valid_warning else 'Not found or incorrect',
            'expected':  'GOVERNMENT WARNING: (standard text)',
            'status':    warning_status,
            'note':      warning_note
        },
    ]

    has_fails    = any(f['status'] == 'fail'    for f in fields)
    has_warnings = any(f['status'] == 'warning' for f in fields)

    overall = 'rejected' if has_fails else ('review' if has_warnings else 'approved')

    return {
        'overallStatus': overall,
        'summary':       'All fields verified.' if overall == 'approved'
                         else 'One or more fields require attention.',
        'fields':        fields
    }

if __name__ == "__main__":

    # Load in model
    model = load_model()
   
    app_data = {
        "brand_name": "ABC",
        "class_type": "single barrel straight Rye Whisky",
        "alcohol_content": "44% ALC/VOL",
        "net_contents": "750ml",
        "producer_name": "ABC Distillery Frederick, MD",
        "country_of_origin": "USA",
        "government_warning": GOV_WARNING_STR
    }
    
    image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1_chatgpt-upscale.png"

    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    img = cv2.imread(image_path)
    _, buffer = cv2.imencode('.png', img)
    image_bytes = buffer.tobytes()
    
    start_time = time.perf_counter()
    verify_label_results = verify_label(model, image_bytes, app_data)
    stop_time = time.perf_counter()
    elapsed_time = stop_time - start_time
    
    print()
    for field in verify_label_results:
        if field == "fields":
            field_subset = verify_label_results[field]
            for item in field_subset:
                print(f"{item}")
            print()
        else:
            print(f"{field}: {verify_label_results[field]}\n")
    print()
    print("Total processing time:", elapsed_time)
    print()