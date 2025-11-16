# Local File Storage (Without Google Drive)

## Overview

The Ebook Generator now supports **automatic fallback to local file storage** when Google Drive credentials are not configured. This makes it easy to use the application for development, testing, or standalone deployments without requiring Google Drive setup.

## How It Works

The application automatically detects storage availability in this order:

1. **Google Drive (Priority)**: If `GOOGLE_CREDENTIALS_PATH` exists and is valid, Google Drive is used
2. **Local Filesystem (Fallback)**: If Google Drive is unavailable, files are saved locally to `./storage/`

### Auto-Detection Logic

```python
# From repository_factory.py
def get_file_storage(self) -> FileStoragePort:
    credentials_path = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json"
    )
    use_drive = os.path.exists(credentials_path)

    if use_drive:
        try:
            drive_adapter = GoogleDriveStorageAdapter()
            if drive_adapter.is_available():
                logger.info("✅ Using Google Drive storage")
                return drive_adapter
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Google Drive: {e}")

    # Fallback to local storage
    storage_path = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    logger.info(f"✅ Using local file storage at: {storage_path}")
    return LocalFileStorageAdapter(storage_path=storage_path)
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Google Drive Configuration (OPTIONAL)
# If not set, the system will use local file storage automatically
GOOGLE_CREDENTIALS_PATH=credentials/google_credentials.json

# Local File Storage Configuration
# Path where generated PDFs will be stored locally
LOCAL_STORAGE_PATH=./storage
```

### Storage Structure

When using local storage, files are organized as follows:

```
storage/
└── ebooks/
    ├── My_Ebook_Title_Cover_KDP.pdf
    ├── My_Ebook_Title_Interior_KDP.pdf
    ├── Another_Book_Cover_KDP.pdf
    └── Another_Book_Interior_KDP.pdf
```

## Usage

### Development Mode (No Google Drive)

1. **Don't create** `credentials/google_credentials.json`
2. Run the application normally:
   ```bash
   make run
   ```
3. Files will be saved to `./storage/ebooks/`
4. Check logs for confirmation:
   ```
   ✅ Using local file storage at: ./storage
   ```

### Production Mode (With Google Drive)

1. Create `credentials/google_credentials.json` with your Google service account credentials
2. Set `GOOGLE_CREDENTIALS_PATH` in `.env`
3. Run the application:
   ```bash
   make run
   ```
4. Files will be uploaded to Google Drive
5. Check logs for confirmation:
   ```
   ✅ Using Google Drive storage (credentials found)
   ```

## Storage Adapter Interface

Both storage backends implement the same `FileStoragePort` interface:

```python
class FileStoragePort(ABC):
    @abstractmethod
    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Upload ebook file to storage"""
        pass

    @abstractmethod
    async def update_ebook(
        self, file_id: str, file_bytes: bytes, filename: str
    ) -> dict[str, str]:
        """Update existing ebook file"""
        pass

    @abstractmethod
    async def get_file_info(self, file_id: str) -> dict[str, str]:
        """Get information about a stored file"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if storage service is available"""
        pass
```

## Return Format

Both adapters return the same standardized format:

### Google Drive Response
```python
{
    "storage_id": "1a2b3c4d5e6f7g8h9i",  # Google Drive file ID
    "storage_url": "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i/view",
    "storage_status": "uploaded",
    "storage_type": "google_drive",
    "filename": "My_Ebook_Cover.pdf"
}
```

### Local Storage Response
```python
{
    "storage_id": "/absolute/path/to/storage/ebooks/My_Ebook_Cover.pdf",
    "storage_url": "file:///absolute/path/to/storage/ebooks/My_Ebook_Cover.pdf",
    "storage_status": "uploaded",
    "storage_type": "local_filesystem",
    "filename": "My_Ebook_Cover.pdf"
}
```

## Benefits

### For Development
- ✅ **No Google credentials needed** for local development
- ✅ **Faster testing** (no network I/O)
- ✅ **Easy file inspection** (just open `./storage/ebooks/`)
- ✅ **Git-friendly** (`storage/` is in `.gitignore`)

### For Production
- ✅ **Automatic Google Drive integration** when credentials exist
- ✅ **Graceful degradation** if Drive quota exceeded or unavailable
- ✅ **Zero code changes** required to switch between modes

## Testing

### Unit Tests

The local storage adapter has comprehensive unit tests:

```bash
# Test local storage adapter
pytest src/backoffice/features/ebook/shared/infrastructure/adapters/tests/test_local_file_storage_adapter.py -v

# 10 tests covering:
# - Directory initialization
# - File upload/update/info
# - Filename sanitization
# - Error handling
```

### Manual Testing

1. **Test local storage mode:**
   ```bash
   # Remove Google credentials (or rename the file)
   mv credentials/google_credentials.json credentials/google_credentials.json.bak

   # Run the app
   make run

   # Create an ebook and approve it
   # Check that files appear in ./storage/ebooks/
   ls -lh storage/ebooks/
   ```

2. **Test Google Drive mode:**
   ```bash
   # Restore Google credentials
   mv credentials/google_credentials.json.bak credentials/google_credentials.json

   # Run the app
   make run

   # Create an ebook and approve it
   # Check logs for "Using Google Drive storage"
   ```

## Troubleshooting

### Issue: Files not being saved

**Check:**
1. Storage path exists and is writable:
   ```bash
   ls -ld storage/
   ```
2. Application logs for errors:
   ```bash
   tail -f logs/app.log | grep storage
   ```

### Issue: Google Drive not being used despite credentials

**Check:**
1. Credentials file path is correct:
   ```bash
   echo $GOOGLE_CREDENTIALS_PATH
   ls -l credentials/google_credentials.json
   ```
2. Credentials file is valid JSON:
   ```bash
   python -m json.tool credentials/google_credentials.json
   ```

### Issue: Permission denied when writing to storage

**Solution:**
```bash
# Create storage directory with correct permissions
mkdir -p storage/ebooks
chmod 755 storage/ebooks
```

## Migration Guide

### From Google Drive to Local Storage

1. No code changes needed
2. Simply remove or rename `credentials/google_credentials.json`
3. Restart the application
4. Files will now be saved locally

### From Local Storage to Google Drive

1. Create Google service account and download credentials
2. Save credentials to `credentials/google_credentials.json`
3. Set `GOOGLE_CREDENTIALS_PATH` in `.env`
4. Restart the application
5. New files will be uploaded to Drive

**Note:** Existing local files will NOT be automatically migrated to Drive. You need to manually upload them if needed.

## Security Considerations

### Local Storage
- Files are stored **unencrypted** on the local filesystem
- Access control depends on filesystem permissions
- Recommended for development/testing only

### Google Drive
- Files benefit from Google's encryption at rest and in transit
- Access control via Google IAM and Drive sharing
- Recommended for production use

## Future Enhancements

Potential improvements for future versions:

- [ ] Add S3-compatible storage adapter (AWS S3, MinIO, etc.)
- [ ] Support for multiple storage backends simultaneously
- [ ] Automatic migration tool (local → Drive)
- [ ] Storage usage metrics and quotas
- [ ] File compression/optimization before upload
- [ ] Storage backend selection via admin UI

## See Also

- [Google Drive Setup Guide](./GOOGLE_DRIVE_SETUP.md) (if exists)
- [Architecture Documentation](../ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md) (if exists)
