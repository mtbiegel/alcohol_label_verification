import cv2
import time
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

# ── Setup ─────────────────────────────────────────────────────────────────────

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device.upper()}")

print("Loading Real-ESRGAN model...")
load_start = time.perf_counter()

model = RRDBNet(
    num_in_ch=3,
    num_out_ch=3,
    num_feat=64,
    num_block=23,
    num_grow_ch=32,
    scale=4
)

upsampler = RealESRGANer(
    scale=4,
    model_path="RealESRNet_x4plus.pth",  # Better for text
    model=model,
    tile=256,
    tile_pad=10,
    pre_pad=0,
    half=False
)

print(f"Model loaded in {time.perf_counter() - load_start:.2f}s")
print("-" * 40)

# ── Upscale ───────────────────────────────────────────────────────────────────

image_path  = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1.png"
output_path = "upscaled_output.png"

img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
print(f"Original size: {img.shape[1]}x{img.shape[0]}")

start = time.perf_counter()
output, _ = upsampler.enhance(img, outscale=4)
stop  = time.perf_counter()

cv2.imwrite(output_path, output)

print(f"Upscaled size: {output.shape[1]}x{output.shape[0]}")
print(f"Upscale time:  {stop - start:.2f}s")
print(f"Saved to:      {output_path}")