# api/api.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import label_ocr  # your existing function

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your SvelteKit dev server
    allow_methods=["POST"],
    allow_headers=["*"]
)

def process_result(result, app_data):
    fields = []
    all_labels_pass = True
    for item in result:

        status = "pass"

        if (not result[item]):
            all_labels_pass = False
            status = "fail"

        item_populate = {
            "field": item,
            "extracted": "not extracting yet",
            "expected": app_data[item],
            "status": status, # "pass" | "fail" | "warning"
            "note": None
        }
        fields.append(item_populate)

    overall_status = "approved" # "approved" | "rejected" | "review"
    summary = "All fields match the application data."
    if not all_labels_pass:
        overall_status = "rejected"
        summary = "One or more fields do NOT match the application data."

    final_result = {
        "overallStatus": overall_status,  
        "summary": summary,
        "fields": fields
    }

    return final_result


@app.post("/verify")
async def verify(image: UploadFile = File(...), applicationData: str = Form(...)):

    print("At API endpoint")
    image_bytes = await image.read()
    app_data = json.loads(applicationData)
    
    print("APP DATA:\n", app_data)
    

    model = label_ocr.load_model()
    print("Loaded Model")    

    print("Starting backend...")
    result, debug_string = label_ocr.verify_label(model, image_bytes, app_data)

    print()
    print("Debug string:\n", debug_string)
    print()
    final_result = process_result(result, app_data)
    print("FINISHED")
    print()
    print(final_result)
    print()

    return final_result