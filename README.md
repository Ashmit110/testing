# Google Drive Text Ingestion Pipeline

This project contains a two-step pipeline designed to securely download files from a specific Google Drive folder and incrementally convert them into plain `.txt` files for ingestion into LLMs or RAG pipelines.

The pipeline consists of two scripts:
1. `sync_from_drive.py`: Uses `rclone` to selectively download only new or changed files from Google Drive.
2. `convert_to_txt.py`: Incrementally parses the downloaded files (PDFs, DOCX, XLSX, CSVs) and converts them to plain text, skipping files whose contents have not changed locally.

---

## 1. Prerequisites

### System Dependencies
The text conversion script requires several system-level libraries for Optical Character Recognition (OCR) and PDF/Word document processing.

On Ubuntu/Debian, install these using:
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils libreoffice tesseract-ocr
```

### Python Dependencies
Install the required Python packages for Excel parsing and the OCR wrapper:
```bash
pip install openpyxl pytesseract Pillow --break-system-packages
```

### Rclone Installation
The sync script relies on `rclone` for robust, multi-threaded downloading and automatic extraction of native Google Workspace documents.

Install the latest version of rclone:
```bash
sudo -v ; curl https://rclone.org/install.sh | sudo bash
```

---

## 2. Rclone Configuration (Important)

For the `sync_from_drive.py` script to work, it **strictly expects** an `rclone` remote to be configured and named exactly: **`acad_material`**.

Follow these exact steps to configure it on your machine:

1. Run the interactive config wizard:
   ```bash
   rclone config
   ```
2. Type `n` for a New remote.
3. Name it exactly: `acad_material`
4. For Storage Type, look for "Google Drive" in the list and enter its corresponding number.
5. Leave "Client ID" and "Client Secret" blank (press Enter).
6. For Scope, choose `1` (Full access).
7. Leave "Service Account file" blank (press Enter).
8. When asked "Edit advanced config?", enter `n`.
9. When asked "Use auto config?", enter `y`. Your web browser will open.
10. Log in to your Google Account and grant rclone access.
11. When asked if this is a Shared Drive (Team Drive), answer `n` (unless the target is explicitly a shared workspace drive).
12. Confirm the configuration and press `q` to quit.

---

## 3. Usage Guide

### Step 1: Sync Files from Google Drive
Run the sync script to pull down files from Google Drive. It will automatically export any Google Docs or Google Sheets as `.docx` and `.xlsx` files respectively.

**Synopsis:**
```bash
python3 sync_from_drive.py <gdrive_folder_name> <local_download_dir>
```

**Example:**
If the folder on Google Drive is named `docs_for_hackenza` and you want to download them into a local folder named `raw_data`:
```bash
python3 sync_from_drive.py "docs_for_hackenza" ./raw_data
```

### Step 2: Convert Downlaoded Files to TXT
Run the conversion script to parse the raw files into flat text files. The script tracks file hashes using a hidden `.conversion_manifest.json` file in the output directory, ensuring that unchanged files are not redundantly processed on subsequent runs.

**Synopsis:**
```bash
python3 convert_to_txt.py <local_download_dir> <text_output_dir>
```

**Example:**
To convert the data downloaded in Step 1 and output the results into a folder named `processed_texts`:
```bash
python3 convert_to_txt.py ./raw_data ./processed_texts
```

If you want to force the script to ignore the hash manifest and reprocess everything from scratch, append the `--force` flag:
```bash
python3 convert_to_txt.py ./raw_data ./processed_texts --force
```
