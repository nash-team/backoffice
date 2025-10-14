#!/usr/bin/env python3
"""
Upload ebook artifacts to Google Drive.

This script handles the upload of generated ebook files to Google Drive
using service account credentials, organizing them by date.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


class DriveUploader:
    """Handle Google Drive uploads with proper folder structure."""

    def __init__(self, credentials_path: str):
        """
        Initialize Drive uploader with service account credentials.

        Args:
            credentials_path: Path to service account JSON file
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/drive"]
        )
        self.service = build("drive", "v3", credentials=self.credentials)

    def create_folder_if_not_exists(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive if it doesn't exist.

        Args:
            folder_name: Name of the folder to create
            parent_id: ID of the parent folder (None for root)

        Returns:
            Folder ID
        """
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"

        try:
            response = (
                self.service.files()
                .list(q=query, spaces="drive", fields="files(id, name)")
                .execute()
            )

            files = response.get("files", [])
            if files:
                # Folder exists, return its ID
                return files[0]["id"]

            # Create new folder
            file_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
            if parent_id:
                file_metadata["parents"] = [parent_id]

            folder = self.service.files().create(body=file_metadata, fields="id").execute()

            print(f"Created folder: {folder_name}")
            return folder["id"]

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise

    def create_folder_path(self, path_parts: List[str]) -> str:
        """
        Create a nested folder structure and return the final folder ID.

        Args:
            path_parts: List of folder names forming the path

        Returns:
            ID of the final folder
        """
        parent_id = None
        for folder_name in path_parts:
            parent_id = self.create_folder_if_not_exists(folder_name, parent_id)
        return parent_id

    def upload_file(
        self, file_path: str, folder_id: str, mime_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to the file
            folder_id: ID of the Drive folder to upload to
            mime_type: MIME type of the file

        Returns:
            Dictionary with file ID and web view link
        """
        file_name = os.path.basename(file_path)

        # Determine MIME type if not provided
        if not mime_type:
            ext = Path(file_path).suffix.lower()
            mime_types = {
                ".pdf": "application/pdf",
                ".zip": "application/zip",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
            }
            mime_type = mime_types.get(ext, "application/octet-stream")

        file_metadata = {"name": file_name, "parents": [folder_id]}

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        try:
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )

            print(f"Uploaded: {file_name}")
            return {"id": file.get("id"), "link": file.get("webViewLink")}

        except HttpError as error:
            print(f"An error occurred uploading {file_name}: {error}")
            raise

    def make_file_shareable(self, file_id: str) -> None:
        """
        Make a file publicly accessible via link.

        Args:
            file_id: Google Drive file ID
        """
        try:
            self.service.permissions().create(
                fileId=file_id, body={"type": "anyone", "role": "reader"}
            ).execute()
        except HttpError as error:
            print(f"An error occurred making file shareable: {error}")


def load_specification(spec_file: str) -> Dict[str, Any]:
    """Load ebook specification from YAML file."""
    with open(spec_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_github_comment(pr_number: int, comment: str, repo: Optional[str] = None) -> None:
    """
    Add a comment to a GitHub pull request.

    Args:
        pr_number: Pull request number
        comment: Comment text
        repo: Repository in format "owner/repo"
    """
    import requests

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set, skipping PR comment")
        return

    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            print("Warning: Repository not specified, skipping PR comment")
            return

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.post(url, headers=headers, json={"body": comment})
        response.raise_for_status()
        print("Posted comment to PR")
    except Exception as e:
        print(f"Failed to post comment: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload ebook artifacts to Google Drive")
    parser.add_argument("--spec", required=True, help="Path to specification YAML file")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing artifacts")
    parser.add_argument(
        "--credentials", required=True, help="Path to Google service account credentials"
    )
    parser.add_argument("--pr-number", type=int, help="Pull request number for posting results")
    parser.add_argument("--repo", help="Repository (owner/repo format)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be uploaded without doing it"
    )

    args = parser.parse_args()

    try:
        # Load specification
        print(f"Loading specification from {args.spec}...")
        spec = load_specification(args.spec)

        # Prepare folder structure
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m-%B")
        ebook_folder = f"ebook-{spec['issue_number']}-{spec['theme']}"

        folder_path = ["Ebooks", year, month, ebook_folder]

        print(f"Target folder structure: {'/'.join(folder_path)}")

        if args.dry_run:
            print("DRY RUN MODE - No actual upload")
            print("\nFiles to upload:")
            artifacts_path = Path(args.artifacts_dir)
            for file in artifacts_path.glob("*"):
                if file.is_file():
                    print(f"  - {file.name} ({file.stat().st_size / 1024:.1f} KB)")
            return 0

        # Initialize Drive uploader
        print("Initializing Google Drive connection...")
        uploader = DriveUploader(args.credentials)

        # Create folder structure
        print("Creating folder structure...")
        folder_id = uploader.create_folder_path(folder_path)

        # List of files to upload
        files_to_upload = [
            ("interior.pdf", "application/pdf"),
            ("cover.pdf", "application/pdf"),
            ("kdp-package.zip", "application/zip"),
            ("preview.pdf", "application/pdf"),
            ("costs.json", "application/json"),
            ("provenance.json", "application/json"),
        ]

        # Upload files
        print("\nUploading files...")
        uploaded_files = {}
        artifacts_path = Path(args.artifacts_dir)

        for file_name, mime_type in files_to_upload:
            file_path = artifacts_path / file_name
            if file_path.exists():
                result = uploader.upload_file(str(file_path), folder_id, mime_type)
                uploaded_files[file_name] = result
                # Make PDFs shareable
                if file_name.endswith(".pdf"):
                    uploader.make_file_shareable(result["id"])
            else:
                print(f"Warning: {file_name} not found, skipping")

        # Upload thumbnails if present
        thumbnails_path = artifacts_path / "thumbnails"
        if thumbnails_path.exists() and thumbnails_path.is_dir():
            print("\nUploading thumbnails...")
            thumbnails_folder_id = uploader.create_folder_if_not_exists("thumbnails", folder_id)
            for thumbnail in thumbnails_path.glob("*.png"):
                uploader.upload_file(str(thumbnail), thumbnails_folder_id, "image/png")

        # Create summary
        print("\n✅ Upload completed successfully!")
        print(f"\n📁 Google Drive folder: {'/'.join(folder_path)}")

        # Prepare comment for PR
        if args.pr_number and uploaded_files:
            comment = "## 📦 Fichiers uploadés vers Google Drive\n\n"
            comment += f"**Dossier**: `{'/'.join(folder_path)}`\n\n"
            comment += "### Liens directs:\n"

            for file_name, info in uploaded_files.items():
                if info.get("link"):
                    emoji = "📖" if file_name.endswith(".pdf") else "📦"
                    comment += f"- {emoji} [{file_name}]({info['link']})\n"

            # Load costs if available
            costs_file = artifacts_path / "costs.json"
            if costs_file.exists():
                with open(costs_file, "r") as f:
                    costs = json.load(f)
                comment += f"\n### 💰 Coût de génération\n"
                comment += f"- Tokens utilisés: {costs.get('tokens', 'N/A')}\n"
                comment += f"- Coût estimé: ${costs.get('estimated_usd', 0):.4f} USD\n"

            comment += "\n---\n"
            comment += "✅ L'ebook a été généré et sauvegardé avec succès!"

            create_github_comment(args.pr_number, comment, args.repo)

        # Write results to file for GitHub Actions output
        results = {
            "success": True,
            "folder_path": "/".join(folder_path),
            "uploaded_files": uploaded_files,
            "timestamp": datetime.now().isoformat(),
        }

        results_file = Path(args.artifacts_dir) / "upload_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
