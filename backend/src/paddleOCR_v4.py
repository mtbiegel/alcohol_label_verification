import os
import time
import logging
import re
import cv2
from cv2 import dnn_superres
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

    all_text = " ".join(text_list).upper()
    if ("GOVERNMENT WARNING" in all_text):
        gov_warning_exists = True

    if (gov_warning_exists):
        start = all_text.find(start_word)
        stop = all_text.find(end_word) + len(end_word)
        gov_str = all_text[start:stop]

        # print("\n-------------------")
        # print(gov_str)
        # print(GOV_WARNING_STR.upper())
        # print("-------------------\n")

        # Need to use fuzzy to determine if it's close but not perfect (aka manual review)
        if (gov_str == GOV_WARNING_STR.upper()):
            matching_ratio = 100.0
        else:
            matching_ratio = fuzz.partial_ratio(gov_str, GOV_WARNING_STR.upper())

        if (matching_ratio == 100.0):
            # print("GOV WARNING - EXACT MATCH:", matching_ratio)
            return True
        elif (matching_ratio >= 95):
            # print("GOV WARNING - PARTIAL MATCH - NEED MANUAL REVIEW:", matching_ratio)
            return False
        else:
            # print("GOV WARNING - NOT EXACT MATCH, NOT EVEN PARTIAL:", matching_ratio)
            return False
    else:
        # print("NO WARNING FOUND")
        return False

    
    return False

def preprocess(img):
    ### Scales up
    # h, w = img.shape[:2]
    # # Only upscale if image is smaller than 1200px on longest side
    # if max(h, w) < 1200:
    #     scale = 1200 / max(h, w)
    #     img = cv2.resize(img, None, fx=scale, fy=scale, 
    #                     interpolation=cv2.INTER_LANCZOS4)

    # ### Contrast
    # lab   = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    # l, a, b = cv2.split(lab)
    # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    # l     = clahe.apply(l)
    # img   = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # ### Sharpen
    # kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    # img = cv2.filter2D(img, -1, kernel)
    # return img

    sr = dnn_superres.DnnSuperResImpl_create()
    sr.readModel("EDSR_x4.pb")
    sr.setModel("edsr", 4)

    result = sr.upsample(img)

    return result

def process_image_ocr(img):
    return ocr.predict(img)

def main(testing_file_name, image_type):
    
    has_brand_name = False
    has_class_type = False
    has_abv = False
    has_net_contents = False
    has_location = False

    # Paths to applicaiton (JSON) and label (image)
    image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/" + testing_file_name + image_type
    json_path = "/home/biegemt1/projects/alcohol_label_verification/tests/applications/" + testing_file_name + ".json"
    print(f"\nProcessing: {image_path}")
    print("=" * 60)

    # Read in application via json
    application_data = read_json_file(json_path)

    # Load in label image
    img = cv2.imread(image_path)

    # print("Running preprocessing...")
    # img = preprocess(img)
    # cv2.imwrite("upscaled.png", img)
    # print("Finished preprocessing")

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

    # print("Ordered Output:", text_result_list)
    # print()
    # print("SINGLE STRING:", text_result_single_string)
    # print()

    application_data_modified = {}
    for item in application_data:
        application_data_modified[item] = application_data[item].replace(" ", "").lower()

    # print("application_data_modified:", application_data_modified)
    # print()
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

    # # Determine if label passes or fails
    # if (has_abv and has_brand_name and has_class_type and has_net_contents and has_valid_gov_warning):
    #     print("LABEL PASSES: All fields are present and valid")
    # else:
    #     print("LABEL FAILS----------------------")
    #     print("Brand Name match?", has_brand_name)
    #     print("Class Type match?", has_class_type)
    #     print("ABV match?", has_abv)
    #     print("Net Contents match?", has_net_contents)
    #     print("Gov Warning match?", has_valid_gov_warning)

    return {"brand_name": [has_brand_name,],
            "class_type": has_class_type,
            "alcohol_content": has_abv,
            "net_contents": has_net_contents,
            "gov_warning": has_valid_gov_warning,
    }

    total_stop_time = time.perf_counter()

    elapsed_time = stop_time - start_time
    total_time = total_stop_time - total_start_time
    # print("\nOCR time:", elapsed_time)
    # print("Total script time:", total_time)

def run_tests():
    
    expected_results = read_json_file("/home/biegemt1/projects/alcohol_label_verification/tests/expected_results.json")
    for item in expected_results:
        file_name = item
        extension = expected_results[item]["image_type"]
        single_result_dict = expected_results[item]["expected_values"]

        results_dict = main(file_name, extension)

        print("\nOUTPUT for", file_name,"-")
        print(single_result_dict)
        print(results_dict)
        print()

        if (single_result_dict == results_dict):
            print("OUPTUT is EXPECTED; SUCCESS")
        else:
            print("------------------------INCORRECT OUTPUT - The following did not match------------------------")
            if (single_result_dict["brand_name"] != results_dict["brand_name"]):
                print("Brand Name:", single_result_dict["brand_name"], "!=", results_dict["brand_name"])

            if (single_result_dict["class_type"] != results_dict["class_type"]):
                print("Class Type match?", single_result_dict["class_type"], "!=", results_dict["class_type"])

            if (single_result_dict["alcohol_content"] != results_dict["alcohol_content"]):
                print("ABV match?", single_result_dict["alcohol_content"], "!=", results_dict["alcohol_content"])
            
            if (single_result_dict["net_contents"] != results_dict["net_contents"]):
                print("Net Contents match?", single_result_dict["net_contents"], "!=", results_dict["net_contents"])
            
            if (single_result_dict["gov_warning"] != results_dict["gov_warning"]):
                print("Gov Warning match?", single_result_dict["gov_warning"], "!=", results_dict["gov_warning"])



if __name__ == "__main__":

    print("Loading PaddleOCR model...")
    ocr = PaddleOCR(
        lang='en',
        device='cpu',
        use_textline_orientation=True,
        use_doc_orientation_classify=True,
        use_doc_unwarping=True
    )

    run_tests()

    # run_single_image()


    # test_file_name = "1.png"
    # split_name = test_file_name.split(".")
    # main(split_name[0], split_name[1])







    # TODO: Need to determine if rotating & unwrapping are necessary (if not can run quicker model). Not a core requirement
        # Need to calculate resolution and dpi of image to let user know if it will be more or less accurate (OCR isn't perfect)
        # Add option for longer, more accurate scanning in GUI and enable these options, but disable them by default. 
        # Automatically rerun ones that are labeled as partial matches with the more accurate model
    
    # TODO: Document how this can be improved
        # - Using a GPU
        # - Using a local LLM trained specifically for text recognition

    # NOTE: Requirement to run this code is to have a processor that supports AVX512/AVX2 at least