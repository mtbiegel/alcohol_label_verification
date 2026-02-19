import asyncio
import label_classifier
import glob
import json
from openai import RateLimitError
import httpx

MAX_CONCURRENT_JOBS_NUM = 5
BATCH_DELAY_SECONDS = 4   # Pause between batches to stay under TPM limit
MAX_RETRIES = 10

async def verify_with_retry(image, app_data):
    for attempt in range(MAX_RETRIES):
        try:
            return await label_classifier.verify_label(image, app_data)
            print(f"No rate limit or JSON parsing issues")
        except (RateLimitError, httpx.HTTPStatusError) as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait_time = (2 ** attempt) + 0.5
            print(f"Rate limit hit, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(wait_time)
        except json.JSONDecodeError:
            # Don't retry parse errors - they won't fix themselves
            print("JSON parse error - skipping this item")
            return None  # or some sentinel value

# Launch n number of processes in parallel
async def process_batch(total_batch, max_concurrent_jobs=MAX_CONCURRENT_JOBS_NUM, show_print_statements=False):

    total_batch_results = []
    for i in range(0, len(total_batch), max_concurrent_jobs):
        batch_results = []
        batch = total_batch[i:i+max_concurrent_jobs]

        if show_print_statements:
            print(f"Processing batch {i // max_concurrent_jobs + 1}, size: {len(batch)}")
        
        batch_results = await asyncio.gather(*(verify_with_retry(item[0], item[1]) for item in batch))
        total_batch_results.extend(batch_results)

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
        
        all_results = asyncio.run(process_batch(image_app_pairing), show_print_statements=True)

        print(f"\nTOTAL BATCH RESULTS - Length: {len(all_results)}:")
        print(json.dumps(all_results, indent=2))