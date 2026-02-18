# api/api.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import label_classifier

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

    # model = label_classifier.load_model()
    # print("Loaded Model")    

    # print()
    # print("APP DATA:")
    # print(json.dumps(app_data, indent=2))
    # print()

    print("Starting backend...")
    result = label_classifier.verify_label(image_bytes, app_data)
    print("Finished backend")
    
    # print()
    # for field in result:
    #     if field == "fields":
    #         field_subset = result[field]
    #         for item in field_subset:
    #             print(f"{item}")
    #         print()
    #     else:
    #         print(f"{field}: {result[field]}\n")
    # print()

    print()
    print("RESULTS:")
    print(json.dumps(result, indent=2))
    print()

    return result