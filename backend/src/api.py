# MIT License
# Copyright (c) 2026 Mark Biegel
# LICENSE file for full license text.

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import label_classifier
import batch_processor
import os
import uvicorn

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Initialize FastAPI app and configure CORS middleware to allow POST requests from the SvelteKit dev server
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # your SvelteKit dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/verify-batch")
async def verify_batch(
    images: List[UploadFile] = File(...), applicationData: str = Form(...)
):
    """
    API endpoint to verify a batch of alcohol label images against provided application data.
    Reads all uploaded images and application data, formats necessary fields, pairs them,
    and runs batch verification. Returns a list of verification results.
    """

    # Log entry into batch endpoint and number of images to process
    print(f"[INFO] At batch verify API endpoint - processing {len(images)} images")

    # Parse application data JSON from form (expects a list of objects)
    try:
        app_data_list = json.loads(applicationData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid applicationData JSON")

    # Validate that the number of images matches the number of application data entries
    if len(images) != len(app_data_list):
        raise HTTPException(
            status_code=400,
            detail="Number of images must match number of application data entries",
        )

    # Initialize list for results and image/application pairings
    results = []
    image_app_pairing = []

    # Read each image and format its corresponding application data
    for i in range(len(images)):
        # Read image bytes
        try:
            image_bytes = await images[i].read()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"verify_batch(): Failed to read in images from batch: {e}",
            )

        # Combine fields into single strings for classifier
        app_data_list[i]["alcohol_content"] = (
            f"{app_data_list[i]['alcohol_content_amount']} {app_data_list[i]['alcohol_content_format']}"
        )
        app_data_list[i]["net_contents"] = (
            f"{app_data_list[i]['net_contents_amount']} {app_data_list[i]['net_contents_unit']}"
        )

        # Append paired image and application data
        image_app_pairing.append([image_bytes, app_data_list[i]])

    # Process the batch using the asynchronous batch processor
    try:
        results = await batch_processor.process_batch(
            image_app_pairing, len(image_app_pairing)
        )
    except Exception as e:
        print(
            f"[ERROR] verify_batch(): Failed to process image batch. Exiting with error: {e}"
        )
        raise HTTPException(status_code=500, detail="Batch processing failed")

    # Log completion and return results
    print(f"[INFO] Batch processing complete: {len(results)} results")
    return results


@app.post("/verify")
async def verify(image: UploadFile = File(...), applicationData: str = Form(...)):
    """
    API endpoint to verify a single alcohol label image against provided application data.
    Reads the uploaded image and application data, formats necessary fields, and runs
    the label verification function. Returns verification results as a dictionary.
    """

    # Log entry into the endpoint
    print("[INFO] At Single verify API endpoint")

    # Read uploaded image bytes
    try:
        image_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"verify_batch(): Failed to read in images from batch: {e}",
        )

    # Parse application data JSON from form
    try:
        app_data = json.loads(applicationData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid applicationData JSON")

    # Combine fields into single strings for classifier
    app_data["alcohol_content"] = (
        f"{app_data['alcohol_content_amount']} {app_data['alcohol_content_format']}"
    )
    app_data["net_contents"] = (
        f"{app_data['net_contents_amount']} {app_data['net_contents_unit']}"
    )

    # Call label verification function and handle any errors
    try:
        print("[INFO] Starting processing...")
        result = await label_classifier.verify_label(image_bytes, app_data)
        print("Finished procesing")
    except Exception as e:
        print(f"[INFO] verify(): Failed to process image. Exiting with error: {e}")
        raise HTTPException(status_code=500, detail="Image processing failed")

    # Return verification results to client
    return result


if __name__ == "__main__":
    ### Main
    # This main function is used to start the api from the deployed instance

    port = int(os.environ.get("PORT", 8000))  # NOTE: Railway dynimcally sets PORT
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
