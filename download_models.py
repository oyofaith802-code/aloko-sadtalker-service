from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
CHECKPOINTS = ROOT / "checkpoints"
CHECKPOINTS.mkdir(parents=True, exist_ok=True)

FILES = {
    "SadTalker_V0.0.2_256.safetensors":
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors",
    "mapping_00109-model.pth.tar":
        "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar",
    "BFM_Fitting.zip":
        "https://github.com/Winfredy/SadTalker/releases/download/v0.0.2/BFM_Fitting.zip",
}

for filename, url in FILES.items():
    target = CHECKPOINTS / filename

    if target.exists() and target.stat().st_size > 100_000:
        print(f"Already exists: {target}")
        continue

    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, target)
    print(f"Downloaded {filename}")

zip_path = CHECKPOINTS / "BFM_Fitting.zip"
bfm_dir = CHECKPOINTS / "BFM_Fitting"

if zip_path.exists() and not bfm_dir.exists():
    print("Extracting BFM_Fitting...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(CHECKPOINTS)

print("Model download complete.")
