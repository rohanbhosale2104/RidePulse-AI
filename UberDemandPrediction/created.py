"""
create_zip.py
=============
Packages the UberDemandPrediction project into a single distributable
`UberDemandPrediction.zip` archive.

Usage:
    python create_zip.py

Run this script from inside the `UberDemandPrediction/` project root
(the directory that directly contains `backend/`, `trained_models/`,
`requirements.txt`, and this file). It walks the project tree, creates
any directories required by the expected layout if they are missing
(e.g. an empty `trained_models/` folder for your model artifact), and
writes every project file into the zip archive while skipping
environment-specific / generated artifacts (virtualenvs, caches, the
zip itself, and local `.env` secrets).
"""
import os
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ZIP_NAME = "UberDemandPrediction.zip"

# Directories that must exist even if currently empty (e.g. before the
# user has dropped their trained model file in place).
REQUIRED_DIRS = [
    "backend/app/core",
    "backend/app/database",
    "backend/app/ml",
    "backend/app/schemas",
    "backend/app/routes",
    "backend/app/services",
    "backend/app/static/css",
    "backend/app/static/js",
    "backend/app/templates",
    "trained_models",
]

# Substrings that, if present anywhere in a file's relative path, cause
# it to be excluded from the archive.
EXCLUDE_PATTERNS = [
    f"{os.sep}venv{os.sep}",
    f"{os.sep}.venv{os.sep}",
    f"{os.sep}__pycache__{os.sep}",
    f"{os.sep}.git{os.sep}",
    ".pyc",
    ZIP_NAME,
]

# Specific top-level files we never want to ship (local secrets, etc.)
EXCLUDE_FILENAMES = {".env"}


def ensure_required_dirs():
    for rel_dir in REQUIRED_DIRS:
        abs_dir = os.path.join(PROJECT_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        # Keep otherwise-empty directories (like trained_models/) present
        # in the zip by dropping a lightweight placeholder if nothing
        # else exists in them yet.
        if not os.listdir(abs_dir):
            placeholder = os.path.join(abs_dir, ".gitkeep")
            with open(placeholder, "w") as f:
                f.write("")


def should_exclude(rel_path: str) -> bool:
    if os.path.basename(rel_path) in EXCLUDE_FILENAMES:
        return True
    normalized = f"{os.sep}{rel_path}{os.sep}"
    for pattern in EXCLUDE_PATTERNS:
        if pattern in normalized or rel_path.endswith(pattern):
            return True
    return False


def build_zip():
    zip_path = os.path.join(PROJECT_ROOT, ZIP_NAME)
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place so os.walk skips them
            dirs[:] = [
                d for d in dirs
                if d not in (".git", "__pycache__", "venv", ".venv")
            ]

            for filename in files:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, PROJECT_ROOT)

                if should_exclude(rel_path):
                    continue

                # Archive under a top-level "UberDemandPrediction/" folder
                arcname = os.path.join("UberDemandPrediction", rel_path)
                zf.write(abs_path, arcname)
                file_count += 1

    print(f"Wrote {file_count} files into: {zip_path}")


if __name__ == "__main__":
    print("Ensuring required project directories exist...")
    ensure_required_dirs()
    print("Building zip archive...")
    build_zip()
    print("Done. Distribute 'UberDemandPrediction.zip' to deploy the project.")
