# MIT License
# Copyright (c) 2026 Mark Biegel
# LICENSE file for full license text.

import asyncio
import label_classifier
import glob
import json
from openai import RateLimitError
import httpx

### Constants
MAX_CONCURRENT_JOBS_NUM = 5  # Maxmimum concurrent jobs to run
BATCH_DELAY_SECONDS = 4  # Pause between batches to stay under TPM limit
MAX_RETRIES = 12  # Maxmimum number of retries if errors occur


async def verify_with_retry(image: bytes, app_data: dict, batch_img_id: int) -> dict:
    """
    Attempts to verify a label using `verify_label`, automatically retrying on rate limits
    or HTTP errors, and handling JSON parsing errors.

    Parameter values:
        - image<bytes> = raw label image to verify.
        - app_data<dict> = expected values from application/form for comparison.
        - batch_img_id<int> = identifier for logging and tracking retry attempts.

    Return value<dict or None>:
        - Verification results dictionary returned by `verify_label`.
        - Returns None if a JSON parsing error occurs.
        - Raises Exception if all retry attempts fail due to rate limits or HTTP errors.
    """

    # Attempt verification up to MAX_RETRIES
    for attempt in range(MAX_RETRIES):
        try:
            # Call verify_label function
            output = await label_classifier.verify_label(image, app_data)
            print(
                f"[INFO] Batch Image ID: {batch_img_id} - No rate limit or JSON parsing issues"
            )
            return output

        # Handle rate limit or HTTP errors by retrying
        except (RateLimitError, httpx.HTTPStatusError) as e:
            # Base wait time increases with each attempt
            wait_time = float(attempt + 1)
            # Add server-specified "Retry-After" header if present
            if hasattr(e, "response") and "Retry-After" in e.response.headers:
                wait_time += float(e.response.headers["Retry-After"])

            # Log retry attempt and wait
            print(
                f"[WARNING] Batch Image ID {batch_img_id} - Rate limit hit, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(wait_time)

        # Handle JSON parsing errors without retrying
        except json.JSONDecodeError:
            print(
                f"[ERROR] Batch Image ID {batch_img_id} - JSON parse error - skipping this item"
            )
            return None  # or some sentinel value

    # Raise exception if all retry attempts fail
    raise Exception(
        "verify_with_retry() - batch_processor.py: Verification failed unexpectedly"
    )


async def process_batch(
    total_batch: list,
    max_concurrent_jobs: int = MAX_CONCURRENT_JOBS_NUM,
    show_print_statements: bool = False,
) -> list:
    """
    Processes a list of label verification tasks in batches, handling concurrency and
    retry logic, and sanitizes any exceptions in results.

    Parameter values:
        - total_batch<list> = list of tuples containing (image_bytes, application_data) for verification.
        - max_concurrent_jobs<int> = maximum number of verification tasks to run concurrently.
        - show_print_statements<bool> = whether to print progress/logging statements during processing.

    Return value<list>:
        - List of verification results dictionaries for each item in total_batch.
        - Exceptions or invalid results are sanitized to dictionaries with 'error' status.
    """

    # Initialize list to hold results from all batches
    total_batch_results = []

    # Process total_batch in chunks of max_concurrent_jobs
    for i in range(0, len(total_batch), max_concurrent_jobs):
        # Initialize list for current batch results
        batch_results = []

        # Slice the current batch from total_batch
        batch = total_batch[i : i + max_concurrent_jobs]

        # Print batch info if requested
        if show_print_statements:
            print(
                f"[INFO] Processing batch {i // max_concurrent_jobs + 1}, size: {len(batch)}"
            )

        # Run verify_with_retry concurrently for all items in the batch
        batch_results = await asyncio.gather(
            *(
                verify_with_retry(item[0], item[1], batch_img_id=i)
                for i, item in enumerate(batch)
            ),
            return_exceptions=True,
        )

        # Clean results, converting any exceptions into sanitized error dictionaries
        cleaned_results = []
        for result in batch_results:
            if isinstance(result, Exception):
                print(
                    f"[WARNING] batch_result has invalid data: {result}. Sanitizing invalid data...",
                    end="",
                )
                cleaned_results.append(
                    {
                        "overallStatus": "error",
                        "summary": "Processing failed",
                        "fields": [],
                    }
                )
                print("done")
            else:
                cleaned_results.append(result)

        # Append cleaned batch results to total results
        total_batch_results.extend(cleaned_results)

    # Return combined results for all batches
    return total_batch_results


if __name__ == "__main__":
    """
        ABOUT main:
            This main function is used for testing values during development
            The intent is to not use it in any deployed setting or aspect
    """

    # Test with sample images
    images_folder_path = "../../tests/test_images" + "/*"
    application_folder_path = "../../tests/applications" + "/*"

    # Filter only files
    # image_files_name_list = [os.path.join(images_folder_path, f) for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]
    # app_files_name_list = [os.path.join(images_folder_path, f) for f in os.listdir(images_folder_path) if os.path.isfile(os.path.join(images_folder_path, f))]

    # Sorting all files
    image_files_name_list = sorted(glob.glob(images_folder_path))
    app_files_name_list = sorted(glob.glob(application_folder_path))

    # If the list lengths of images and apps don't match, an error occurred
    if len(image_files_name_list) != len(app_files_name_list):
        print("[ERROR] image files and app files are of different quantities")
    else:
        # Pair each image with its corresponding application data for processing
        image_app_pairing = []
        for i in range(len(image_files_name_list)):
            # Read image bytes from file
            with open(image_files_name_list[i], "rb") as f:
                image_bytes = f.read()

            # Load application data from JSON file
            with open(app_files_name_list[i], "r", encoding="utf-8") as f:
                app_data = json.load(f)

            # Append paired image and application data to list
            image_app_pairing.append([image_bytes, app_data])

        # Run batch processing asynchronously for all paired items
        all_results = asyncio.run(
            process_batch(image_app_pairing, show_print_statements=True)
        )

        # Print summary of total batch results
        print(f"\n[INFO] TOTAL BATCH RESULTS - Length: {len(all_results)}:")
        print(json.dumps(all_results, indent=2))
