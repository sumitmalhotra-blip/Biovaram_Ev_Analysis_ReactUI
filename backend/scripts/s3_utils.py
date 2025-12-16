"""
AWS S3 Utilities - Task 1.6
============================

Purpose:
- Upload/download files to/from AWS S3
- Read/write Parquet files directly from S3
- List files in S3 buckets
- Handle S3 errors and retries

Author: CRMIT Team
Date: November 13, 2025
Status: STUB - Implementation pending
"""

import boto3  # type: ignore[import-not-found]
from botocore.exceptions import ClientError  # type: ignore[import-not-found]
import pandas as pd
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Manager:
    """
    Manager for AWS S3 operations.
    """
    
    def __init__(self, config_path: str = "config/s3_config.json"):
        """
        Initialize S3 manager.
        
        Args:
            config_path: Path to S3 configuration file
        """
        self.config = self._load_config(config_path)
        self.s3_client = self._init_s3_client()
        logger.info("S3 Manager initialized")
    
    def _load_config(self, config_path: str | None) -> Dict:
        """Load S3 configuration.
        
        WHAT IT DOES:
        -------------
        Loads AWS S3 configuration from a JSON file containing:
        - bucket_name: Target S3 bucket for data storage
        - region: AWS region (e.g., us-east-1, us-west-2)
        - raw_prefix: S3 folder path for raw FCS/NTA files
        - processed_prefix: S3 folder path for processed Parquet files
        
        WHY THIS DESIGN:
        ----------------
        - Separates configuration from code (12-factor app principle)
        - Allows different configs for dev/staging/production
        - Avoids hardcoding AWS credentials in source code
        - Easy to switch between buckets without code changes
        
        EXAMPLE CONFIG FILE (config/s3_config.json):
        ---------------------------------------------
        {
            "bucket_name": "exosome-analysis-prod",
            "region": "us-east-1",
            "raw_prefix": "raw_data/nanofacs/",
            "processed_prefix": "processed_data/parquet/",
            "aws_access_key_id": "stored_in_environment",
            "aws_secret_access_key": "stored_in_environment"
        }
        """
        # TODO: Load from JSON file
        # Implementation would look like:
        # with open(config_path, 'r') as f:
        #     config = json.load(f)
        # return config
        
        # Default configuration for development
        return {
            "bucket_name": "exosome-analysis-bucket",
            "region": "us-east-1",
            "raw_prefix": "raw_data/",
            "processed_prefix": "processed_data/"
        }
    
    def _init_s3_client(self):
        """Initialize boto3 S3 client.
        
        WHAT IT DOES:
        -------------
        Creates an authenticated AWS S3 client using boto3 library.
        
        AUTHENTICATION METHODS (in order of preference):
        ------------------------------------------------
        1. IAM Role (if running on EC2/ECS/Lambda) - MOST SECURE
           - No credentials in code or config files
           - Automatic credential rotation
           - Recommended for production
        
        2. Environment Variables:
           - AWS_ACCESS_KEY_ID
           - AWS_SECRET_ACCESS_KEY
           - AWS_SESSION_TOKEN (optional, for temporary credentials)
        
        3. AWS Credentials File (~/.aws/credentials):
           - Standard boto3 credential chain
           - Good for local development
        
        4. Config File (LEAST SECURE - avoid for production):
           - Only for local development/testing
           - Never commit credentials to git!
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        import boto3
        from botocore.config import Config
        
        # Configure with retries and timeouts
        boto_config = Config(
            region_name=self.config['region'],
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=10,
            read_timeout=60
        )
        
        # Initialize client (uses AWS credential chain)
        client = boto3.client('s3', config=boto_config)
        
        return client
        """
        # TODO: Initialize with credentials
        # return boto3.client('s3', region_name=self.config['region'])
        raise NotImplementedError("S3 client initialization not yet implemented")
    
    def upload_file(self, local_path: str, s3_path: str) -> bool:
        """
        Upload file to S3 with automatic retry and progress tracking.
        
        Args:
            local_path: Local file path
            s3_path: S3 destination path (s3://bucket/key)
        
        Returns:
            True if successful, False otherwise
        
        HOW IT WORKS:
        -------------
        1. Parse S3 path to extract bucket and key:
           s3://my-bucket/folder/file.fcs → bucket='my-bucket', key='folder/file.fcs'
        
        2. Check if local file exists and is readable
        
        3. Determine upload method based on file size:
           - Small files (<5MB): Simple put_object
           - Large files (>5MB): Multipart upload (faster, resumable)
        
        4. Upload with progress callback (for large files)
        
        5. Retry on failure (network errors, timeouts):
           - Exponential backoff: wait 1s, 2s, 4s between retries
           - Max 3 retries before giving up
        
        6. Verify upload by checking ETag or file size
        
        MULTIPART UPLOAD (for files >5MB):
        ----------------------------------
        - Splits file into 5MB chunks
        - Uploads chunks in parallel (faster)
        - Automatically resumes if interrupted
        - Essential for files >5GB (S3 limit for single upload)
        
        ERROR HANDLING:
        ---------------
        - FileNotFoundError: Local file doesn't exist
        - PermissionError: No read access to local file or write to S3
        - ClientError (NoSuchBucket): S3 bucket doesn't exist
        - ClientError (AccessDenied): Insufficient S3 permissions
        - Timeout: Network issues or slow connection
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        import os
        from botocore.exceptions import ClientError
        
        try:
            # Parse S3 path
            if not s3_path.startswith('s3://'):
                raise ValueError("S3 path must start with s3://")
            
            parts = s3_path[5:].split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ''
            
            # Check file size
            file_size = os.path.getsize(local_path)
            logger.info(f"Uploading {local_path} ({file_size/1e6:.1f} MB) to s3://{bucket}/{key}")
            
            # Upload (with progress tracking for large files)
            if file_size < 5 * 1024 * 1024:  # 5MB
                # Simple upload
                with open(local_path, 'rb') as f:
                    self.s3_client.put_object(Bucket=bucket, Key=key, Body=f)
            else:
                # Multipart upload with progress
                self.s3_client.upload_file(
                    local_path, bucket, key,
                    Callback=ProgressCallback(file_size)
                )
            
            logger.success(f"✅ Upload complete: {s3_path}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
        
        TODO: Implement upload with retry logic
        """
        raise NotImplementedError("S3 upload not yet implemented")
    
    def download_file(self, s3_path: str, local_path: str) -> bool:
        """
        Download file from S3 with automatic retry and verification.
        
        Args:
            s3_path: S3 source path (s3://bucket/key)
            local_path: Local destination path
        
        Returns:
            True if successful, False otherwise
        
        HOW IT WORKS:
        -------------
        1. Parse S3 path (bucket name + object key)
        2. Check if S3 object exists (HeadObject API call)
        3. Create local directory if needed (mkdir -p)
        4. Download file:
           - Small files (<100MB): Direct download to memory, then write
           - Large files (>100MB): Stream download (memory efficient)
        5. Verify download:
           - Compare file size with S3 metadata
           - Optionally verify ETag (MD5 checksum)
        6. Retry on failure (up to 3 times with exponential backoff)
        
        STREAMING DOWNLOAD (for large files):
        -------------------------------------
        Instead of loading entire file into memory:
        1. Open S3 object as stream
        2. Read in chunks (8MB at a time)
        3. Write chunks to local file
        4. Update progress bar
        
        Benefits:
        - Constant memory usage regardless of file size
        - Can download 10GB files on 1GB RAM machine
        - Shows download progress
        
        VERIFICATION:
        -------------
        After download, verify integrity by:
        1. File size matches S3 metadata
        2. ETag matches (MD5 hash for single-part uploads)
        3. If mismatch: delete partial file and retry
        
        ERROR HANDLING:
        ---------------
        - NoSuchKey: S3 object doesn't exist
        - AccessDenied: No read permission for S3 object
        - NoSuchBucket: Bucket doesn't exist
        - PermissionError: Can't write to local directory
        - Timeout: Network issues
        - IncompleteRead: Connection dropped during download
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        import os
        from pathlib import Path
        
        try:
            # Parse S3 path
            parts = s3_path[5:].split('/', 1)
            bucket, key = parts[0], parts[1]
            
            # Check if exists
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            logger.info(f"Downloading {file_size/1e6:.1f} MB from {s3_path}")
            
            # Create local directory
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            self.s3_client.download_file(
                bucket, key, local_path,
                Callback=ProgressCallback(file_size)
            )
            
            # Verify size
            downloaded_size = os.path.getsize(local_path)
            if downloaded_size != file_size:
                raise ValueError(f"Size mismatch: expected {file_size}, got {downloaded_size}")
            
            logger.success(f"✅ Download complete: {local_path}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return False
        
        TODO: Implement download with retry logic
        """
        raise NotImplementedError("S3 download not yet implemented")
    
    def read_parquet_from_s3(self, s3_path: str) -> pd.DataFrame:
        """
        Read Parquet file directly from S3 without downloading to disk.
        
        Args:
            s3_path: S3 path to Parquet file (s3://bucket/key)
        
        Returns:
            DataFrame with Parquet data
        
        WHY THIS IS USEFUL:
        ------------------
        Instead of:
        1. Download 100MB Parquet from S3 to disk (30 seconds)
        2. Read from disk into DataFrame (5 seconds)
        3. Delete temporary file
        Total: 35 seconds + disk space
        
        With direct read:
        1. Stream from S3 directly into DataFrame (20 seconds)
        Total: 20 seconds, no disk usage
        
        HOW IT WORKS:
        -------------
        1. Open S3 object as binary stream (get_object)
        2. Read stream into BytesIO buffer (in-memory file)
        3. Pass buffer to pandas.read_parquet()
        4. Parquet library (pyarrow) reads directly from buffer
        5. Return DataFrame
        
        MEMORY CONSIDERATIONS:
        ----------------------
        - File loads into memory (use for files <1GB)
        - For large files (>1GB), consider:
          a) Reading specific columns only:
             pd.read_parquet(buffer, columns=['VFSC-H', 'VSSC1-H'])
          b) Reading in chunks (if using Dask or filtered queries)
          c) Downloading to disk first (if processing multiple times)
        
        PARQUET ADVANTAGES OVER CSV:
        ----------------------------
        - 5-10× faster to read (columnar format)
        - 50-90% smaller file size (compression)
        - Preserves data types (int, float, datetime)
        - Can read specific columns without loading entire file
        - Built-in metadata (column names, statistics)
        
        ERROR HANDLING:
        ---------------
        - NoSuchKey: Parquet file doesn't exist in S3
        - InvalidParquet: File is corrupted or not valid Parquet
        - MemoryError: File too large to fit in RAM
        - Timeout: Slow S3 connection
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        from io import BytesIO
        import pandas as pd
        
        try:
            # Parse S3 path
            parts = s3_path[5:].split('/', 1)
            bucket, key = parts[0], parts[1]
            
            logger.info(f"Reading Parquet from {s3_path}")
            
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            
            # Read into buffer
            buffer = BytesIO(response['Body'].read())
            
            # Parse Parquet
            df = pd.read_parquet(buffer, engine='pyarrow')
            
            logger.info(f"✅ Loaded {len(df):,} rows, {len(df.columns)} columns ({file_size/1e6:.1f} MB)")
            return df
            
        except ClientError as e:
            logger.error(f"Failed to read Parquet from S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse Parquet: {e}")
            raise
        
        TODO: Implement direct S3 Parquet read
        """
        raise NotImplementedError("S3 Parquet read not yet implemented")
    
    def write_parquet_to_s3(self, df: pd.DataFrame, s3_path: str):
        """
        Write DataFrame to Parquet format directly in S3.
        
        Args:
            df: DataFrame to write
            s3_path: S3 destination path (s3://bucket/key.parquet)
        
        HOW IT WORKS:
        -------------
        1. Convert DataFrame to Parquet in memory (BytesIO buffer)
        2. Compress using Snappy (fast) or Gzip (smaller)
        3. Upload buffer to S3 using put_object
        4. Set appropriate metadata (Content-Type: application/parquet)
        
        COMPRESSION OPTIONS:
        --------------------
        - Snappy (default): 3× faster compression, good ratio (2-5×)
          Best for: Frequent reads, large datasets, real-time processing
        
        - Gzip: Slower compression, better ratio (5-10×)
          Best for: Long-term storage, infrequent reads, cost optimization
        
        - Brotli: Best compression (10-20×), very slow
          Best for: Archive storage, never re-write
        
        PARQUET BENEFITS FOR S3:
        ------------------------
        1. Smaller files = lower S3 storage costs
           100MB CSV → 10MB Parquet = 90% cost reduction
        
        2. Faster queries with S3 Select or Athena:
           - Read only needed columns (columnar format)
           - Query without downloading entire file
           - Built-in predicate pushdown
        
        3. Better data integrity:
           - Schema validation (type checking)
           - Built-in checksums
           - Atomic writes (all-or-nothing)
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        from io import BytesIO
        
        try:
            # Parse S3 path
            parts = s3_path[5:].split('/', 1)
            bucket, key = parts[0], parts[1]
            
            logger.info(f"Writing {len(df):,} rows to {s3_path}")
            
            # Write to buffer with compression
            buffer = BytesIO()
            df.to_parquet(
                buffer,
                engine='pyarrow',
                compression='snappy',  # Fast compression
                index=False  # Don't save DataFrame index
            )
            
            # Get buffer size
            file_size = buffer.tell()
            buffer.seek(0)  # Reset to start
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/parquet',
                Metadata={
                    'rows': str(len(df)),
                    'columns': str(len(df.columns)),
                    'compression': 'snappy'
                }
            )
            
            logger.success(f"✅ Wrote {file_size/1e6:.1f} MB to S3")
            
        except Exception as e:
            logger.error(f"Failed to write Parquet to S3: {e}")
            raise
        
        TODO: Implement direct S3 Parquet write
        """
        raise NotImplementedError("S3 Parquet write not yet implemented")
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List all files in S3 bucket with given prefix (folder path).
        
        Args:
            prefix: S3 prefix/folder path (e.g., "raw_data/nanofacs/")
        
        Returns:
            List of S3 paths (s3://bucket/key)
        
        HOW IT WORKS:
        -------------
        S3 doesn't have true "folders" - it's a flat key-value store.
        But we can simulate folders using key prefixes:
        
        Keys in bucket:
        - "raw_data/nanofacs/sample1.fcs"
        - "raw_data/nanofacs/sample2.fcs"
        - "raw_data/nta/measurement1.csv"
        
        list_files("raw_data/nanofacs/") returns:
        - ["s3://bucket/raw_data/nanofacs/sample1.fcs",
           "s3://bucket/raw_data/nanofacs/sample2.fcs"]
        
        PAGINATION:
        -----------
        S3 ListObjects returns max 1000 keys per request.
        For buckets with >1000 files, we need pagination:
        
        1. Call list_objects_v2(Prefix=prefix, MaxKeys=1000)
        2. Get 1000 keys + continuation token
        3. Call again with ContinuationToken
        4. Repeat until IsTruncated=False
        
        FILTERING:
        ----------
        You can filter results by:
        - Prefix: "folder" path
        - Suffix: file extension (in code, not API)
        - Date: LastModified timestamp
        - Size: file size in bytes
        
        Example - find all .parquet files from last 7 days:
        all_files = list_files("processed_data/")
        parquet_files = [f for f in all_files if f.endswith('.parquet')]
        recent = [f for f in parquet_files if was_modified_recently(f)]
        
        COST OPTIMIZATION:
        ------------------
        ListObjects costs $0.005 per 1,000 requests.
        For 100,000 files = 100 requests = $0.50
        
        To reduce costs:
        1. Use specific prefixes (don't list entire bucket)
        2. Cache results (if files don't change often)
        3. Use S3 Inventory (daily manifest of all objects)
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        try:
            bucket = self.config['bucket_name']
            logger.info(f"Listing files in s3://{bucket}/{prefix}")
            
            files = []
            continuation_token = None
            
            # Paginate through all results
            while True:
                # Build request parameters
                params = {'Bucket': bucket, 'Prefix': prefix}
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                # List objects
                response = self.s3_client.list_objects_v2(**params)
                
                # Extract keys
                if 'Contents' in response:
                    for obj in response['Contents']:
                        s3_path = f"s3://{bucket}/{obj['Key']}"
                        files.append(s3_path)
                
                # Check if more results
                if not response.get('IsTruncated'):
                    break
                
                continuation_token = response.get('NextContinuationToken')
            
            logger.info(f"✅ Found {len(files)} files")
            return files
            
        except ClientError as e:
            logger.error(f"Failed to list S3 files: {e}")
            return []
        
        TODO: Implement file listing
        """
        raise NotImplementedError("S3 file listing not yet implemented")


def main():
    """Main entry point for S3 utilities."""
    logger.info("S3 Utilities - Implementation pending")
    logger.info("See TASK_TRACKER.md Task 1.6 for requirements")


if __name__ == "__main__":
    main()
