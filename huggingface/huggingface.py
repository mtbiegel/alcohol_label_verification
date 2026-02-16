import time

# pip install transformers torch torchvision Pillow

from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
import torch

# ── Load Model ────────────────────────────────────────────────────────────────

print("Loading Florence-2 model...")
load_start = time.perf_counter()

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device.upper()}")

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base",
    trust_remote_code=True,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32
).to(device)

processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-base",
    trust_remote_code=True
)

print(f"Model loaded in {time.perf_counter() - load_start:.2f}s")
print("-" * 40)


# ── OCR Function ──────────────────────────────────────────────────────────────

def extract_text(image_path: str) -> str:
    """
    Extract all text from an image using Florence-2's OCR task.
    Returns the extracted text as a string.
    """
    image = Image.open(image_path).convert("RGB")

    # Florence-2 has a dedicated OCR task
    prompt = "<OCR>"

    inputs = processor(
        text=prompt,
        images=image,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3
        )

    result = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        result,
        task="<OCR>",
        image_size=(image.width, image.height)
    )

    return parsed.get("<OCR>", "").strip()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/9.png"

    print(f"Processing: {image_path}")
    print("=" * 60)

    start = time.perf_counter()
    text  = extract_text(image_path)
    stop  = time.perf_counter()

    print("Extracted text:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    print(f"OCR time: {stop - start:.2f}s")