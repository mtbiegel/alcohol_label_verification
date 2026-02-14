import easyocr

# Create reader (specify language(s))
reader = easyocr.Reader(['en'])  # English

# reader = easyocr.Reader(
#     ['en'],
#     model_storage_directory='/home/mtbiegel/take_home/easyOCR_offline_models',
#     download_enabled=False  # prevents automatic download
# )


# Read image
results = reader.readtext("/home/mtbiegel/take_home/tests/test_images/brand-label-new1.jpg")

# Print detected text
for (bbox, text, confidence) in results:
    print(f"Text: {text}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Bounding Box: {bbox}")
    print("-" * 30)



# Edge cases:

