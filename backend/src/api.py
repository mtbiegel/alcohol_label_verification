# api/api.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
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

@app.post("/verify-batch")
async def verify_batch(images: List[UploadFile] = File(...), applicationData: str = Form(...)):
    print(f"At batch verify API endpoint - processing {len(images)} images")
    
    # Parse the batch application data (array of objects)
    app_data_list = json.loads(applicationData)
    
    if len(images) != len(app_data_list):
        return {"ERROR": "Number of images must match number of application data entries"}
    
    # Process all pairs
    results = []
    image_app_pairing = []
    for i in range(len(images)):

        image_bytes = await images[i].read()

        # Combine into single string for the classifier
        app_data_list[i]['alcohol_content'] = f"{app_data_list[i]['alcohol_content_amount']} {app_data_list[i]['alcohol_content_format']}"
        app_data_list[i]['net_contents'] = f"{app_data_list[i]['net_contents_amount']} {app_data_list[i]['net_contents_unit']}"

        image_app_pairing.append([image_bytes, app_data_list[i]])

    results = await batch_processor.process_batch(image_app_pairing, len(image_app_pairing))
    
    print(f"Batch processing complete: {len(results)} results")
    return results

@app.post("/verify")
async def verify(image: UploadFile = File(...), applicationData: str = Form(...)):

    print("At Single verify API endpoint")
    image_bytes = await image.read()
    app_data = json.loads(applicationData)

    # Combine into single string for the classifier
    app_data['alcohol_content'] = f"{app_data['alcohol_content_amount']} {app_data['alcohol_content_format']}"
    app_data['net_contents'] = f"{app_data['net_contents_amount']} {app_data['net_contents_unit']}"

    print("Starting processing...")
    result = await label_classifier.verify_label(image_bytes, app_data)
    print("Finished procesing")

    return result