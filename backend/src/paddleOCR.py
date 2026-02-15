import os
import time

# Must be set before importing paddleocr to disable OneDNN
# which causes a NotImplementedError on some CPUs
os.environ["FLAGS_use_mkldnn"] = "0"

from paddleocr import PaddleOCR

# Updated API for newer versions of PaddleOCR:
# - use_textline_orientation replaces use_angle_cls
# - device='cpu' replaces use_gpu=False
print("Loading PaddleOCR model...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en', device='cpu')

# Path to your test image
image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/2.png"

print(f"\nProcessing: {image_path}")
print("=" * 60)

start_time = time.perf_counter()

# Run OCR using predict() - ocr() is deprecated in newer versions
results = ocr.predict(image_path)

stop_time = time.perf_counter()

for item in results:
    for field in item:
        if field.strip() == "rec_texts":
            text_result_list = item[field]
            print(field, ":\n", text_result_list)
            print("\n--------------------------------------\n")

# Need to determine if there is a divide so it can be ready appropraitely
# Need to rotate the image the correct way before OCR-ing?

# Need to clean output array

#Requirement to run this code is to have a processor that supports AVX512/AVX2 at least

elapsed_time = stop_time - start_time
print("Elapsed time:", elapsed_time)