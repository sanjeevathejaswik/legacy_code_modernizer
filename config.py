import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT",   "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT",  "")

# Key is read from the terminal environment variable — never stored in .env or code
# Set before running:  $env:AZURE_OPENAI_KEY_GPT4o = "<your-key>"  (PowerShell)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY_GPT4o", "")

MAX_AUDIT_RETRIES    = int(os.getenv("MAX_AUDIT_RETRIES",    "2"))
AUDIT_PASS_THRESHOLD = float(os.getenv("AUDIT_PASS_THRESHOLD", "70.0"))
OUTPUT_DIR           = os.getenv("OUTPUT_DIR",               "output")

MAX_BUILD_RETRIES    = int(os.getenv("MAX_BUILD_RETRIES",    "1"))
BUILD_TIMEOUT_SECS   = int(os.getenv("BUILD_TIMEOUT_SECS",   "120"))
