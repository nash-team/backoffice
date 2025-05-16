import os
from pathlib import Path

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials", "google_credentials.json")

# Configuration Google Drive
GOOGLE_DRIVE_FOLDER_ID = "1okwSaBe0_P9Hkfw3MWf9P4dUKtSKX2zN" 