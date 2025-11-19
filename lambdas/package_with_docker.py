#!/usr/bin/env python3
"""
Alternative packaging script using Docker for Linux-compatible builds
This solves the cryptography import issue on Windows
"""

import os
import subprocess
import shutil
import tempfile
from zipfile import ZipFile

LAMBDA_DIR = "packaged"
FUNCTIONS = [
    ("packages_handler", "packages_handler.py"),
    ("tracks_handler", "tracks_handler.py"),
    ("address_handler", "address_handler.py"),
    ("depots_handler", "depots_handler.py"),
    ("images_handler", "images_handler.py"),
    ("notifications_handler", "notifications_handler.py"),
    ("user_handler", "user_handler.py"),
]

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def package_with_docker(function_name: str, source_file: str):
    """Package Lambda using Docker (Linux-compatible)"""
    print(f"\n Packaging {function_name} with Docker...")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    build_dir = os.path.join(temp_dir, "build")
    os.makedirs(build_dir, exist_ok=True)
    
    # Copy source files
    shutil.copy(source_file, build_dir)
    if os.path.isfile("email_templates.py"):
        shutil.copy("email_templates.py", build_dir)
    
    # Copy requirements.txt
    if os.path.isfile("requirements.txt"):
        shutil.copy("requirements.txt", build_dir)
    
    # Create Dockerfile
    dockerfile_content = f"""
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt ${os.environ.get('LAMBDA_TASK_ROOT', '/var/task')}/
RUN pip install --no-cache-dir -r requirements.txt -t ${{LAMBDA_TASK_ROOT}}

# Copy function code
COPY {source_file} ${{LAMBDA_TASK_ROOT}}/
"""
    if os.path.isfile("email_templates.py"):
        dockerfile_content += f"COPY email_templates.py ${{LAMBDA_TASK_ROOT}}/\n"
    
    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)
    
    # Build Docker image
    image_name = f"lambda-{function_name}:latest"
    print(f"→ Building Docker image...")
    result = subprocess.run(
        ["docker", "build", "-t", image_name, "-f", dockerfile_path, build_dir],
        check=True
    )
    
    # Extract files from Docker container
    container_name = f"lambda-{function_name}-extract"
    print(f"→ Extracting files from container...")
    
    # Create container
    subprocess.run(
        ["docker", "create", "--name", container_name, image_name],
        check=True,
        capture_output=True
    )
    
    # Extract to temp directory
    extract_dir = os.path.join(temp_dir, "extract")
    os.makedirs(extract_dir, exist_ok=True)
    
    subprocess.run(
        ["docker", "cp", f"{container_name}:/var/task/.", extract_dir],
        check=True
    )
    
    # Clean up container
    subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    # Create ZIP
    os.makedirs(LAMBDA_DIR, exist_ok=True)
    zip_path = os.path.join(LAMBDA_DIR, f"{function_name}.zip")
    
    with ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(extract_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, start=extract_dir)
                zipf.write(full_path, arcname)
    
    # Clean up
    shutil.rmtree(temp_dir)
    print(f"✅ {function_name} packaged successfully → {zip_path}")

def main():
    if not check_docker():
        print("❌ Docker not found. Please install Docker Desktop or use the regular script.py")
        print("   The regular script will attempt to use platform-specific pip flags.")
        return
    
    print("🐳 Using Docker for Linux-compatible packaging...")
    os.makedirs(LAMBDA_DIR, exist_ok=True)
    
    for fn, src in FUNCTIONS:
        try:
            package_with_docker(fn, src)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error packaging {fn}: {e}")
            return
    
    print("\n✅ All Lambda functions packaged successfully with Docker!\n")

if __name__ == "__main__":
    main()

