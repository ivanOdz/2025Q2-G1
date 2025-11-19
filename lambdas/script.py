import os
import shutil
import tempfile
import json
import sys
import hashlib
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------
# CONFIG
# -----------------------------
LAMBDA_DIR = "packaged"

FUNCTIONS = [
    ("packages_handler", "packages_handler.py"),
    ("tracks_handler", "tracks_handler.py"),
    ("address_handler", "address_handler.py"),
    ("depots_handler", "depots_handler.py"),
    ("images_handler", "images_handler.py"),
    ("notifications_handler", "notifications_handler.py"),
    ("user_handler","user_handler.py"),
]

# -----------------------------
# Helpers
# -----------------------------
def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return None
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    return sha.hexdigest()

def should_rebuild(function_name: str, source_file: str):
    """Returns True if Lambda ZIP needs to be rebuilt"""
    zip_path = os.path.join(LAMBDA_DIR, f"{function_name}.zip")
    cache_file = os.path.join(LAMBDA_DIR, f".{function_name}.cache")

    if not os.path.exists(zip_path):
        return True

    if not os.path.exists(cache_file):
        return True

    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
    except:
        return True

    # Compare source file hash
    if cache.get("source_hash") != get_file_hash(source_file):
        return True

    # Compare email templates if used
    if os.path.isfile("email_templates.py"):
        if cache.get("templates_hash") != get_file_hash("email_templates.py"):
            return True

    return False

def save_cache(function_name: str, source_file: str):
    """Save build metadata for incremental builds."""
    cache_file = os.path.join(LAMBDA_DIR, f".{function_name}.cache")
    cache = {
        "source_hash": get_file_hash(source_file),
        "templates_hash": get_file_hash("email_templates.py") if os.path.isfile("email_templates.py") else None
    }
    with open(cache_file, "w") as f:
        json.dump(cache, f)

# -----------------------------
# Packaging Logic
# -----------------------------
def package_lambda(function_name: str, source_file: str):
    print(f"\n📦 Packaging {function_name}...")

    if not should_rebuild(function_name, source_file):
        print(f"→ Skipping {function_name} (no changes detected)")
        return

    temp_dir = tempfile.mkdtemp()

    # Copy main handler
    shutil.copy(source_file, temp_dir)

    # Copy templates if used
    if os.path.isfile("email_templates.py"):
        shutil.copy("email_templates.py", temp_dir)

    # Create ZIP
    zip_path = os.path.join(LAMBDA_DIR, f"{function_name}.zip")
    os.makedirs(LAMBDA_DIR, exist_ok=True)

    excluded_patterns = ['__pycache__', '.pyc', '.pyo', '.egg-info', '.dist-info']

    with ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(temp_dir):
            if "__pycache__" in root:
                continue

            for f in files:
                full = os.path.join(root, f)
                if any(p in full for p in excluded_patterns):
                    continue
                arcname = os.path.relpath(full, temp_dir)
                zipf.write(full, arcname)

    # Save cache
    save_cache(function_name, source_file)

    # Cleanup
    shutil.rmtree(temp_dir)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"✅ {function_name} packaged → {zip_path} ({size_mb:.2f} MB)")

# -----------------------------
# Main
# -----------------------------
def main():
    print("\n🚀 Starting optimized Lambda packaging...")
    os.makedirs(LAMBDA_DIR, exist_ok=True)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(package_lambda, fn, src): fn
            for fn, src in FUNCTIONS
        }

        failures = []
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"❌ Error packaging {name}: {e}")
                failures.append(name)

    print("\n===============================")
    print(" Packaging Summary")
    print("===============================")

    if failures:
        print(f"❌ Failed: {failures}")
        sys.exit(1)
    else:
        print("✅ All Lambda functions packaged successfully!")

if __name__ == "__main__":
    main()
