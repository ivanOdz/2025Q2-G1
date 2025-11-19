#!/usr/bin/env python3
"""
Script para construir el Lambda Layer de SendGrid
Ejecutar antes de hacer terraform apply si el layer no existe
"""

import sys
import shutil
from pathlib import Path
from subprocess import run

LAYER_DIR = Path("lambdas/layer/python/lib/python3.11/site-packages")
LAYER_ZIP = Path("lambdas/layer/sendgrid-layer.zip")

def build_layer():
    print("\n=== BUILDING LAMBDA LAYER ===")

    layer_root = Path("lambdas/layer")
    python_root = layer_root / "python"
    site_packages = python_root / "lib" / "python3.11" / "site-packages"

    # Clean previous layer
    if layer_root.exists():
        print("→ Cleaning old layer directory...")
        shutil.rmtree(layer_root)

    print(f"→ Creating layer directory: {site_packages}")
    site_packages.mkdir(parents=True, exist_ok=True)

    # Install dependencies into site-packages
    print("→ Installing sendgrid==6.12.4 into layer...")
    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        "sendgrid==6.12.4",
        "-t",
        str(site_packages)
    ], check=True)

    # Remove dist-info and test folders
    print("→ Cleaning unnecessary metadata...")
    for item in site_packages.iterdir():
        if item.suffix in [".dist-info", ".egg-info"]:
            shutil.rmtree(item, ignore_errors=True)
        if item.name.endswith("tests"):
            shutil.rmtree(item, ignore_errors=True)

    # Create ZIP
    print(f"→ Creating layer ZIP: {LAYER_ZIP}")
    LAYER_ZIP.parent.mkdir(exist_ok=True)

    if LAYER_ZIP.exists():
        LAYER_ZIP.unlink()

    shutil.make_archive(
        base_name=str(LAYER_ZIP.with_suffix("")),
        format="zip",
        root_dir=str(layer_root),
        base_dir="python"
    )

    print(f"✅ Layer built successfully → {LAYER_ZIP}")

if __name__ == "__main__":
    try:
        build_layer()
    except Exception as e:
        print(f"❌ Error building layer: {e}")
        sys.exit(1)

