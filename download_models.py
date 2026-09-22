from pathlib import Path
import urllib.request

CHECKPOINTS = Path("checkpoints")
CHECKPOINTS.mkdir(exist_ok=True)

FILES = {
    "SadTalker_V0.0.2_256.safetensors":
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors",
    "mapping_00109-model.pth.tar":
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar",
}

for filename, url in FILES.items():
    target = CHECKPOINTS / filename
    if target.exists() and target.stat().st_size > 100_000_000:
        print(f"Already exists: {target}")
        continue

    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, target)
    print(f"Downloaded: {target}")

print("Model download complete.")