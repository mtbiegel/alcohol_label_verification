# api/api.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
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
    try:
        app_data_list = json.loads(applicationData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid applicationData JSON")

    
    if len(images) != len(app_data_list):
        raise HTTPException(
            status_code=400,
            detail="Number of images must match number of application data entries"
        )
    
    # Process all pairs
    results = []
    image_app_pairing = []
    for i in range(len(images)):

        try:
            image_bytes = await images[i].read()
        except:
            raise HTTPException(status_code=400, detail="verify_batch(): Failed to read in images from batch.")

        # Combine into single string for the classifier
        app_data_list[i]['alcohol_content'] = f"{app_data_list[i]['alcohol_content_amount']} {app_data_list[i]['alcohol_content_format']}"
        app_data_list[i]['net_contents'] = f"{app_data_list[i]['net_contents_amount']} {app_data_list[i]['net_contents_unit']}"

        image_app_pairing.append([image_bytes, app_data_list[i]])

    try:
        results = await batch_processor.process_batch(image_app_pairing, len(image_app_pairing))
    except Exception as e:
        print(f"verify_batch(): Failed to process image batch. Exiting with error: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

    
    print(f"Batch processing complete: {len(results)} results")
    return results

@app.post("/verify")
async def verify(image: UploadFile = File(...), applicationData: str = Form(...)):

    print("At Single verify API endpoint")
    try:
        image_bytes = await image.read()
    except:
        raise HTTPException(status_code=400, detail="verify_batch(): Failed to read in images from batch.")

    # Parse the batch application data (array of objects)
    try:
        app_data = json.loads(applicationData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid applicationData JSON")

    # Combine into single string for the classifier
    app_data['alcohol_content'] = f"{app_data['alcohol_content_amount']} {app_data['alcohol_content_format']}"
    app_data['net_contents'] = f"{app_data['net_contents_amount']} {app_data['net_contents_unit']}"

    try:
        print("Starting processing...")
        result = await label_classifier.verify_label(image_bytes, app_data)
        print("Finished procesing")
    except Exception as e:
        print(f"verify(): Failed to process image. Exiting with error: {e}")
        raise HTTPException(status_code=500, detail="Image processing failed")

    return result