#!/usr/bin/env python

import sys
import os
import subprocess
import shutil
from pathlib import Path

# =================================================================
# USE FROM PROJECT ROOT:
#     python scripts/deploy_all.py <dev|prod>
# =================================================================

LAYER_DIR = Path("lambdas/layer/python/lib/python3.11/site-packages")
LAYER_ZIP = Path("lambdas/layer/sendgrid-layer.zip")
LAMBDA_SCRIPT = "script.py"


# -----------------------------------------------------------------
# Helper
# -----------------------------------------------------------------
def run(cmd, cwd=None):
    """Run command with visible output and stop on error."""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd)


# =================================================================
# 1. BUILD LAYER (SendGrid + Deps)
# =================================================================
def build_layer():
    print("\n=== BUILDING LAMBDA LAYER ===")

    layer_root = Path("lambdas/layer")                      # lambdas/layer/
    python_root = layer_root / "python"                     # lambdas/layer/python/
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
    ])

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
        root_dir=str(layer_root),   # <--- FIXED
        base_dir="python"           # <--- FIXED
    )

    print(f"✅ Layer built successfully → {LAYER_ZIP}")


# =================================================================
# 2. PACKAGE LAMBDAS
# =================================================================
def build_lambdas():
    print("\n=== PACKAGING LAMBDA FUNCTIONS ===")

    lambdas_dir = "lambdas"
    original_dir = os.getcwd()

    try:
        os.chdir(lambdas_dir)

        python_cmd = "python" if shutil.which("python") else "python"

        run([python_cmd, LAMBDA_SCRIPT])

    finally:
        os.chdir(original_dir)


# =================================================================
# 3. TERRAFORM DEPLOY
# =================================================================
def terraform_deploy(env):
    print("\n=== TERRAFORM DEPLOY ===")

    terraform_dir = f"envs/{env}"
    tfvars_file = f"{env}.tfvars"

    if not os.path.isdir(terraform_dir):
        print(f"❌ ERROR: Terraform directory not found: {terraform_dir}")
        sys.exit(1)

    original = os.getcwd()
    os.chdir(terraform_dir)

    try:
        print("→ terraform init")
        run(["terraform", "init"])

        print("→ terraform apply")
        run(["terraform", "apply", "-auto-approve", f"-var-file={tfvars_file}"])

        # Get outputs
        def tf_output(name):
            return subprocess.check_output(
                ["terraform", "output", "-raw", name],
                text=True
            ).strip()

        outputs = {
            "bucket": tf_output("frontend_bucket_name"),
            "api_url": tf_output("api_gateway_invoke_url"),
            "pool_id": tf_output("cognito_user_pool_id"),
            "client_id": tf_output("cognito_user_pool_client_id"),
            "websocket_url": tf_output("websocket_api_endpoint"),
        }

        print("\n--- Terraform Outputs ---")
        for k, v in outputs.items():
            print(f"{k}: {v}")

    except subprocess.CalledProcessError:
        print("❌ ERROR: Failed to get terraform outputs.")
        sys.exit(1)

    finally:
        os.chdir(original)

    return outputs


# =================================================================
# 4. DEPLOY FRONTEND
# =================================================================
def deploy_frontend(outputs):
    print("\n=== FRONTEND DEPLOY ===")

    python_cmd = "python" if shutil.which("python") else "python"
    deploy_script = "./scripts/deploy_frontend.py"

    run([
        python_cmd,
        deploy_script,
        outputs["bucket"],
        outputs["api_url"],
        outputs["pool_id"],
        outputs["client_id"],
        outputs["websocket_url"]
    ])

    print("✅ Frontend deployment complete.")


# =================================================================
# MAIN
# =================================================================
def main():
    if len(sys.argv) != 2:
        print("Usage: python deploy_all.py <dev|prod>")
        sys.exit(1)

    env = sys.argv[1]

    print("\n=======================================")
    print(f"🚀 DEPLOYING ENVIRONMENT: {env}")
    print("=======================================\n")

    build_layer()
    build_lambdas()

    outputs = terraform_deploy(env)
    deploy_frontend(outputs)

    print("\n==========================================")
    print(f"🎉 Deployment for environment '{env}' COMPLETED")
    print("==========================================\n")


if __name__ == "__main__":
    main()
