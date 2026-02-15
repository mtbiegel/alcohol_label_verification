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

GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.")

def sort_text(results, img_width: int, img_height: int) -> list:
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

def read_json_file(filename):
    """
    Reads data from a JSON file and returns a Python dictionary or list.
    """
    try:
        # Open the file in read mode ('r') using a context manager
        with open(filename, 'r') as file:
            # Use json.load() to parse the file content directly
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from the file '{filename}'. Check the file's format.")
        return None

def check_government_warning(text_list: list) -> bool:
     
    gov_warning_exists = False
    start = 0
    stop = 0

    start_word = "GOVERNMENT"
    end_word = "PROBLEMS."

    all_text = " ".join(text_list)
    if ("GOVERNMENT WARNING" in all_text):
        gov_warning_exists = True

    if (gov_warning_exists):
        start = all_text.find(start_word)
        stop = all_text.find(end_word)
        gov_str = all_text[start:stop].upper()
        
        print("\n-------------------")
        print(gov_str)
        print(GOV_WARNING_STR.upper())
        print("-------------------\n")

        # Need to use fuzzy to determine if it's close but not perfect (aka manual review)
        partial_ratio = fuzz.partial_ratio(gov_str, GOV_WARNING_STR.upper())
        print("PARTIAL RATIO:", partial_ratio)

        if (partial_ratio == 100):
            print("EXACT MATCH")
            return True
        elif (partial_ratio >= 95):
            print("PARTIAL MATCH - NEED MANUAL REVIEW:", partial_ratio)
            return False
        else:
            print("NOT EXACT MATCH, NOT EVEN PARTIAL:", partial_ratio)
            return False
    else:
        print("NO WARNING FOUND")
        return False

    
    return False

def process_image_ocr(img):
    return ocr.predict(img)

def main(testing_file_name):
    
    has_brand_name = False
    has_class_type = False
    has_abv = False
    has_net_contents = False
    has_location = False

    # Paths to applicaiton (JSON) and label (image)
    image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/" + testing_file_name + ".png"
    json_path = "/home/biegemt1/projects/alcohol_label_verification/tests/applications/" + testing_file_name + ".json"
    print(f"\nProcessing: {image_path}")
    print("=" * 60)

    # Read in application via json
    application_data = read_json_file(json_path)

    # Load in label image
    img = cv2.imread(image_path)

    start_time = time.perf_counter()
    # Run paddleOCR on label to get text
    results = process_image_ocr(img)
    stop_time = time.perf_counter()

    # Sort output from paddleOCR so text is chronological
    text_result_list = sort_text(results, img.shape[1], img.shape[0])

    # for item in results:
    #     for field in item:
    #         if field == "rec_texts":
    #             print("\n\nOriginal Output:", item[field])

    # Check if gov warning is 100% correct
    has_valid_gov_warning = check_government_warning(text_result_list)

    # Combine into 1 string and convert to lowercase.
    # TODO: Remove gov warning text for less possible errors???
    text_result_single_string = "".join(text_result_list).replace(" ", "").lower()

    print("Ordered Output:", text_result_list)
    print()

    print("SINGLE STRING:", text_result_single_string)
    print()

    application_data_modified = {}
    for item in application_data:
        application_data_modified[item] = application_data[item].replace(" ", "").lower()

    print("application_data_modified:", application_data_modified)
    print()

    # print("----------------")
    # print(application_data)
    # print(application_data_modified)
    # print("----------------")


    # Check if label has correct brand_name
    if (application_data_modified["brand_name"] in text_result_single_string):
        has_brand_name = True

    if (application_data_modified["class_type"] in text_result_single_string):
        has_class_type = True

    if (application_data_modified["alcohol_content"] in text_result_single_string):
        has_abv = True

    if (application_data_modified["net_contents"] in text_result_single_string):
        has_net_contents = True

    # Determine if label passes or fails
    if (has_abv and has_brand_name and has_class_type and has_net_contents and has_valid_gov_warning):
        print("LABEL PASSES: All fields are present and valid")
    else:
        print("LABEL FAILS----------------------")
        print("Brand Name Passes?", has_brand_name)
        print("Class Type Passes?", has_class_type)
        print("ABV Passes?", has_abv)
        print("Net Contents Passes?", has_net_contents)
        print("Gov Warning Passes?", has_valid_gov_warning)

    total_stop_time = time.perf_counter()

    elapsed_time = stop_time - start_time
    total_time = total_stop_time - total_start_time
    print("\nOCR time:", elapsed_time)
    print("Total script time:", total_time)


if __name__ == "__main__":
    print("Loading PaddleOCR model...")
    ocr = PaddleOCR(
        lang='en',
        device='cpu',
        use_textline_orientation=True,
        use_doc_orientation_classify=True,
        use_doc_unwarping=True
    )

    test_file_name = "10"
    main(test_file_name)

    # TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model). Not a core requirement
        # Add option for longer, more accurate scanning in GUI and enable these options, but disable them by default. 
        # Automatically rerun ones that are labeled as partial matches with the more accurate model
    
    # NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least