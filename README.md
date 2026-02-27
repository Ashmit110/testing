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
Install the required Python packages: `python-dotenv` (for loading credentials), `openpyxl` (for Excel parsing), and the OCR wrappers.
```bash
pip install python-dotenv openpyxl pytesseract Pillow --break-system-packages
```

### Rclone Installation
The sync script relies on `rclone` for robust, multi-threaded downloading and automatic extraction of native Google Workspace documents.

Install the latest version of rclone:
```bash
sudo -v ; curl https://rclone.org/install.sh | sudo bash
```

---

## 2. How Authentication Works

This pipeline has been designed to be incredibly easy to run on any machine without complex authentication wizards.

Instead of requiring each user to log into their personal Google account, we use a **Google Cloud Service Account** (a "dummy/robot account"). We simply share the target Google Drive folder with this robot account, and the robot downloads the files for us!

### What you need to do:
To run the sync script, you need **three things**:
1. A `.env` file containing the robot account's credentials. (The project administrator will provide this file directly to you).
2. The URL of the Google Drive folder you want to sync.
3. **Share the Drive folder with the Service Account email.** This is *not* someone's personal Google account — it's a special email generated when the Service Account was created, in the form:
   ```
   <name>@<project-id>.iam.gserviceaccount.com
   ```
   You can find this email in the credentials JSON under the `client_email` field. Share the target Drive folder with this email as a **Viewer**.

Simply place the `.env` file in the exact same directory as the Python scripts. The script will automatically parse the credentials and securely pass them to `rclone` in the background. **No manual `rclone config` setup is required!**

---

## 3. Usage Guide

### Step 1: Sync Files from Google Drive
Run the sync script to pull down files from Google Drive. It will automatically export any Google Docs or Google Sheets as `.docx` and `.xlsx` files respectively.

**Synopsis:**
```bash
python3 sync_from_drive.py <drive_link> <dest>
```

**Example:**
If the folder's URL on Google Drive is `https://drive.google.com/drive/folders/1B2a3...` and you want to download the files into a local folder named `raw_data`:
```bash
python3 sync_from_drive.py "https://drive.google.com/drive/folders/1B2a3..." ./raw_data
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
