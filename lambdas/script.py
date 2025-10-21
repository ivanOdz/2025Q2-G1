import os
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

# -----------------------------
# CONFIG
# -----------------------------
LAMBDA_DIR = "lambdas"
FUNCTIONS = [
    ("packages_handler", "packages_handler.py"),
    ("tracks_handler", "tracks_handler.py"),
    ("address_handler", "address_handler.py"),
    ("depots_handler", "depots_handler.py"),
    ("images_handler", "images_handler.py"),
    ("notifications_handler", "notifications_handler.py"),
]

# -----------------------------
# SCRIPT
# -----------------------------
def run(cmd):
    """Run shell command with visible output and error handling"""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def package_lambda(function_name: str, source_file: str):
    print(f"\n Packaging {function_name}...")

    # Create temp dir
    temp_dir = tempfile.mkdtemp()
    shutil.copy(source_file, temp_dir)

    # Install dependencies if requirements.txt exists
    if os.path.isfile("requirements.txt"):
        print("→ Installing dependencies...")
        run(["pip", "install", "-r", "requirements.txt", "-t", temp_dir])

    # Create target dir if needed
    os.makedirs(LAMBDA_DIR, exist_ok=True)

    # Zip content
    zip_path = os.path.join(LAMBDA_DIR, f"{function_name}.zip")
    with ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(temp_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, start=temp_dir)
                zipf.write(full_path, arcname)

    # Clean up
    shutil.rmtree(temp_dir)
    print(f"{function_name} packaged successfully → {zip_path}")

def main():
    print(" Starting Lambda function packaging...")
    os.makedirs(LAMBDA_DIR, exist_ok=True)
    for fn, src in FUNCTIONS:
        package_lambda(fn, src)
    print("\n All Lambda functions packaged successfully!\n")
    print("Next steps:")
    print("Run 'terraform apply' to deploy the infrastructure")

if __name__ == "__main__":
    main()
