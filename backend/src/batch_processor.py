import asyncio
import label_classifier
import glob
import json
from openai import RateLimitError
import httpx

MAX_CONCURRENT_JOBS_NUM = 5
BATCH_DELAY_SECONDS = 4   # Pause between batches to stay under TPM limit
MAX_RETRIES = 12

async def verify_with_retry(image, app_data, batch_img_id):
    for attempt in range(MAX_RETRIES):
        try:
            output = await label_classifier.verify_label(image, app_data)
            print(f"[INFO] Batch Image ID: {batch_img_id} - No rate limit or JSON parsing issues")
            return output
        except (RateLimitError, httpx.HTTPStatusError) as e:
            wait_time = float(attempt+1)
            if hasattr(e, "response") and "Retry-After" in e.response.headers:
                wait_time += float(e.response.headers["Retry-After"])
                
            print(f"[WARNING] Batch Image ID {batch_img_id} - Rate limit hit, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(wait_time)
        except json.JSONDecodeError:
            # Don't retry parse errors - they won't fix themselves
            print(f"[ERROR] Batch Image ID {batch_img_id} - JSON parse error - skipping this item")
            return None  # or some sentinel value

    raise Exception("verify_with_retry() - batch_processor.py: Verification failed unexpectedly")

# Launch n number of processes in parallel
async def process_batch(total_batch, max_concurrent_jobs=MAX_CONCURRENT_JOBS_NUM, show_print_statements=False):

    total_batch_results = []
    for i in range(0, len(total_batch), max_concurrent_jobs):
        batch_results = []
        batch = total_batch[i:i+max_concurrent_jobs]

        if show_print_statements:
            print(f"Processing batch {i // max_concurrent_jobs + 1}, size: {len(batch)}")
        
        batch_results = await asyncio.gather(*(verify_with_retry(item[0], item[1], batch_img_id=i) for i, item in enumerate(batch)), return_exceptions=True)

        cleaned_results = []
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"ERROR - batch_result has invalid data: {result}. Sanitizing invalid data...", end="")
                cleaned_results.append({
                    "overallStatus": "error",
                    "summary": "Processing failed",
                    "fields": []
                })
                print("done")
            else:
                cleaned_results.append(result)

        total_batch_results.extend(cleaned_results)

    return total_batch_results

if __name__ == '__main__':
    
    images_folder_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images" + "/*"
    application_folder_path = "/home/biegemt1/projects/alcohol_label_verification/tests/applications" + "/*"

    # Filter only files
    # image_files_name_list = [os.path.join(images_folder_path, f) for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]
    # app_files_name_list = [os.path.join(images_folder_path, f) for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]

    image_files_name_list = sorted(glob.glob(images_folder_path))
    app_files_name_list = sorted(glob.glob(application_folder_path))

    if (len(image_files_name_list) != len(app_files_name_list)):
        print("ERROR: image files and app files are of different quantities")
    
    else:
        image_app_pairing = []
        for i in range(len(image_files_name_list)):

            with open(image_files_name_list[i], 'rb') as f:
                image_bytes = f.read()

            with open(app_files_name_list[i], 'r', encoding='utf-8') as f:
                app_data = json.load(f)

            image_app_pairing.append([image_bytes, app_data])
        
        all_results = asyncio.run(process_batch(image_app_pairing, show_print_statements=True))

        print(f"\nTOTAL BATCH RESULTS - Length: {len(all_results)}:")
        print(json.dumps(all_results, indent=2))