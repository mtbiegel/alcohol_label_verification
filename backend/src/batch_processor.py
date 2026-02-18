import asyncio
import label_classifier
import glob
import json

MAX_CONCURRENT = 5

# Launch n number of processes in parallel
async def process_batch(total_batch):

    total_batch_results = []
    for i in range(0, len(total_batch), MAX_CONCURRENT):

        print(f"Processing batch {i // MAX_CONCURRENT + 1}, size: {len(batch)}")
        batch_results = []
        batch = total_batch[i:i+MAX_CONCURRENT]        
        
        batch_results = await asyncio.gather(*(label_classifier.verify_label(item[0], item[1]) for item in batch))
        total_batch_results.extend(batch_results)

    # print(json.dumps(app_data, indent=2))
    print(f"TOTAL BATCH RESULTS (len {len(total_batch_results)}):")


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
        
        asyncio.run(process_batch(image_app_pairing))