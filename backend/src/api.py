# api/api.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import label_classifier
import batch_processor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your SvelteKit dev server
    allow_methods=["POST"],
    allow_headers=["*"]
)

@app.post("/verify")
async def verify(image: UploadFile = File(...), applicationData: str = Form(...)):

    print("At API endpoint")
    image_bytes = await image.read()
    app_data = json.loads(applicationData)

    # Combine into single string for the classifier
    app_data['alcohol_content'] = f"{app_data['alcohol_content_amount']} {app_data['alcohol_content_format']}"
    app_data['net_contents'] = f"{app_data['net_contents_amount']} {app_data['net_contents_unit']}"

    print("Starting backend...")
    result = await label_classifier.verify_label(image_bytes, app_data)
    print("Finished backend")

    print()
    print("RESULTS:")
    print(json.dumps(result, indent=2))
    print()

    return result