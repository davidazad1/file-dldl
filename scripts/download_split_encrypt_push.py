#!/usr/bin/env python3
import os
import subprocess
import sys
import requests
from cryptography.fernet import Fernet

# Configurable chunk size (slightly under 100MB to be safe)
CHUNK_SIZE = 40 * 1024 * 1024  # 95 MB

def split_and_encrypt(data, key, base_name="chunk"):
    """Split bytes into chunks, encrypt each, return list of filenames."""
    f = Fernet(key.encode())
    chunks = []
    total = len(data)
    for i, start in enumerate(range(0, total, CHUNK_SIZE)):
        chunk_data = data[start:start+CHUNK_SIZE]
        encrypted = f.encrypt(chunk_data)
        filename = f"{base_name}_{i:03d}.enc"
        with open(filename, "wb") as out:
            out.write(encrypted)
        chunks.append(filename)
    return chunks

def main():
    url = os.environ.get("SECRET_DOWNLOAD_URL")
    key = os.environ.get("ENCRYPTION_KEY")
    output_prefix = os.environ.get("OUTPUT_PREFIX", "encrypted_chunk")

    if not url or not key:
        print("Error: SECRET_DOWNLOAD_URL and ENCRYPTION_KEY must be set")
        sys.exit(1)

    # 1. Download the whole file
    print(f"Downloading from {url} ...")
    try:
        response = requests.get(url, timeout=300)  # longer timeout for large files
        response.raise_for_status()
        data = response.content
    except Exception as e:
        print(f"Download failed: {e}")
        sys.exit(1)

    print(f"Downloaded {len(data)} bytes. Splitting into chunks <= {CHUNK_SIZE} bytes...")

    # 2. Split and encrypt
    chunk_files = split_and_encrypt(data, key, output_prefix)
    print(f"Created {len(chunk_files)} encrypted chunks: {', '.join(chunk_files)}")

    # 3. Git add, commit and push all chunks
    print("Committing and pushing to repository...")
    try:
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add"] + chunk_files, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Add encrypted file chunks [skip ci]"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Push successful.")
        else:
            print("No changes to commit.")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
