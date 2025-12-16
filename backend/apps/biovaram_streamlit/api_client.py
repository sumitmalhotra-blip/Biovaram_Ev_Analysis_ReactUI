"""
API Client for Streamlit App
=============================

Provides Python wrapper functions to communicate with the FastAPI backend.

All API calls go through this client to:
- Centralize error handling
- Provide consistent interface
- Enable easy mocking for tests

Author: CRMIT Team
Date: November 27, 2025
"""

from typing import Optional, Dict, List, Any, BinaryIO
import requests
from pathlib import Path
import os
from loguru import logger


class CRMITAPIClient:
    """Client for CRMIT Backend API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.
        
        Args:
            base_url: Backend API URL (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.timeout = 30  # seconds
        
        logger.info(f"🔌 API Client initialized: {self.base_url}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if backend API is responding.
        
        Returns:
            Health status dictionary
            
        Raises:
            requests.RequestException: If API is unreachable
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Health check failed: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get system status and database connection info.
        
        Returns:
            Status dictionary with version, uptime, database info
        """
        try:
            response = requests.get(
                f"{self.api_base}/status",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Status check failed: {e}")
            raise
    
    # =========================================================================
    # Sample Management
    # =========================================================================
    
    def get_samples(
        self,
        skip: int = 0,
        limit: int = 100,
        treatment: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get list of samples with optional filtering.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            treatment: Filter by treatment name
            status: Filter by processing status (pending, processing, completed, failed)
            
        Returns:
            Dictionary with 'total', 'skip', 'limit', 'samples' keys
            
        Example:
            >>> client.get_samples(limit=10, treatment="CD81")
            {'total': 25, 'skip': 0, 'limit': 10, 'samples': [...]}
        """
        try:
            params = {'skip': skip, 'limit': limit}
            if treatment:
                params['treatment'] = treatment
            if status:
                params['status'] = status
            
            response = requests.get(
                f"{self.api_base}/samples",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get samples: {e}")
            raise
    
    def get_sample_details(self, sample_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a specific sample.
        
        Args:
            sample_id: Database ID of the sample
            
        Returns:
            Sample details including metadata, FCS results, NTA results, QC status
            
        Example:
            >>> client.get_sample_details(42)
            {
                'id': 42,
                'sample_id': 'L5_F10_CD81',
                'treatment': 'CD81',
                'concentration_ug': 1.0,
                'fcs_results': {...},
                'nta_results': {...},
                'qc_status': 'passed'
            }
        """
        try:
            response = requests.get(
                f"{self.api_base}/samples/{sample_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get sample {sample_id}: {e}")
            raise
    
    def delete_sample(self, sample_id: int) -> Dict[str, str]:
        """
        Delete a sample and all its related data.
        
        Args:
            sample_id: Database ID of the sample
            
        Returns:
            Confirmation message
        """
        try:
            response = requests.delete(
                f"{self.api_base}/samples/{sample_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to delete sample {sample_id}: {e}")
            raise
    
    # =========================================================================
    # File Upload
    # =========================================================================
    
    def upload_fcs(
        self,
        file_path: str,
        sample_id: str,
        treatment: Optional[str] = None,
        concentration_ug: Optional[float] = None,
        preparation_method: Optional[str] = None,
        operator: Optional[str] = None,
        notes: Optional[str] = None,
        experiment_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload FCS file with metadata and experiment parameters.
        
        Args:
            file_path: Path to .fcs file
            sample_id: Unique identifier for this sample
            treatment: Treatment/antibody name (e.g., "CD81", "CD9", "Isotype")
            concentration_ug: Antibody concentration in micrograms
            preparation_method: Purification method (SEC, Centrifugation, etc.)
            operator: Name of person who performed experiment
            notes: Additional notes
            experiment_params: Dictionary containing experiment parameters:
                - temperature_celsius: Sample temperature during measurement
                - substrate: Buffer/substrate used (e.g., "PBS (pH 7.4)")
                - volume_ul: Sample volume in microliters
                - ph: Sample pH value
                - incubation_time_min: Incubation time in minutes
                - staining_protocol: Type of staining used
                - dilution_factor: Dilution ratio (e.g., "1:100")
                - instrument_settings: Any special instrument settings
            
        Returns:
            Upload confirmation with sample_id, file_path, processing_status
            
        Example:
            >>> client.upload_fcs(
            ...     file_path="data/sample1.fcs",
            ...     sample_id="L5_F10_CD81",
            ...     treatment="CD81",
            ...     concentration_ug=1.0,
            ...     preparation_method="SEC",
            ...     experiment_params={
            ...         "temperature_celsius": 25.0,
            ...         "substrate": "PBS (pH 7.4)",
            ...         "volume_ul": 50.0,
            ...         "ph": 7.4
            ...     }
            ... )
            {
                'sample_id': 'L5_F10_CD81',
                'message': 'FCS file uploaded successfully',
                'file_path': 'uploads/fcs/sample1.fcs',
                'processing_status': 'pending'
            }
        """
        try:
            # Prepare file for upload
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f, 'application/octet-stream')}
                
                # Prepare form data
                data = {'sample_id': sample_id}
                if treatment:
                    data['treatment'] = treatment
                if concentration_ug is not None:
                    data['concentration_ug'] = str(concentration_ug)
                if preparation_method:
                    data['preparation_method'] = preparation_method
                if operator:
                    data['operator'] = operator
                if notes:
                    data['notes'] = notes
                
                # Add experiment parameters (flatten for form data)
                if experiment_params:
                    if experiment_params.get('temperature_celsius') is not None:
                        data['temperature_celsius'] = str(experiment_params['temperature_celsius'])
                    if experiment_params.get('substrate'):
                        data['substrate'] = experiment_params['substrate']
                    if experiment_params.get('volume_ul') is not None:
                        data['volume_ul'] = str(experiment_params['volume_ul'])
                    if experiment_params.get('ph') is not None:
                        data['ph'] = str(experiment_params['ph'])
                    if experiment_params.get('incubation_time_min') is not None:
                        data['incubation_time_min'] = str(experiment_params['incubation_time_min'])
                    if experiment_params.get('staining_protocol'):
                        data['staining_protocol'] = experiment_params['staining_protocol']
                    if experiment_params.get('dilution_factor'):
                        data['dilution_factor'] = experiment_params['dilution_factor']
                    if experiment_params.get('instrument_settings'):
                        data['instrument_settings'] = experiment_params['instrument_settings']
                
                # Upload
                response = requests.post(
                    f"{self.api_base}/upload/fcs",
                    files=files,
                    data=data,
                    timeout=60  # Longer timeout for file upload
                )
                response.raise_for_status()
                
            logger.success(f"✅ Uploaded FCS file: {sample_id}")
            return response.json()
            
        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            raise
        except requests.RequestException as e:
            logger.error(f"❌ FCS upload failed: {e}")
            raise
    
    def upload_nta(
        self,
        file_path: str,
        sample_id: str,
        treatment: Optional[str] = None,
        concentration_ug: Optional[float] = None,
        preparation_method: Optional[str] = None,
        operator: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload NTA file with metadata.
        
        Args:
            file_path: Path to NTA file (.csv, .xlsx, .txt)
            sample_id: Unique identifier for this sample
            treatment: Treatment/antibody name
            concentration_ug: Sample concentration
            preparation_method: Purification method
            operator: Operator name
            notes: Additional notes
            
        Returns:
            Upload confirmation
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f, 'application/octet-stream')}
                
                data = {'sample_id': sample_id}
                if treatment:
                    data['treatment'] = treatment
                if concentration_ug is not None:
                    data['concentration_ug'] = str(concentration_ug)
                if preparation_method:
                    data['preparation_method'] = preparation_method
                if operator:
                    data['operator'] = operator
                if notes:
                    data['notes'] = notes
                
                response = requests.post(
                    f"{self.api_base}/upload/nta",
                    files=files,
                    data=data,
                    timeout=60
                )
                response.raise_for_status()
                
            logger.success(f"✅ Uploaded NTA file: {sample_id}")
            return response.json()
            
        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            raise
        except requests.RequestException as e:
            logger.error(f"❌ NTA upload failed: {e}")
            raise
    
    # =========================================================================
    # Results Retrieval
    # =========================================================================
    
    def get_fcs_results(self, sample_id: int) -> Dict[str, Any]:
        """
        Get FCS analysis results for a sample.
        
        Args:
            sample_id: Database ID of the sample
            
        Returns:
            FCS results including statistics, gating, etc.
        """
        try:
            response = requests.get(
                f"{self.api_base}/samples/{sample_id}/fcs",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get FCS results for sample {sample_id}: {e}")
            raise
    
    def get_nta_results(self, sample_id: int) -> Dict[str, Any]:
        """
        Get NTA analysis results for a sample.
        
        Args:
            sample_id: Database ID of the sample
            
        Returns:
            NTA results including D10, D50, D90, concentration, etc.
        """
        try:
            response = requests.get(
                f"{self.api_base}/samples/{sample_id}/nta",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get NTA results for sample {sample_id}: {e}")
            raise
    
    # =========================================================================
    # Processing Jobs
    # =========================================================================
    
    def get_jobs(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get list of processing jobs.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            status: Filter by job status (pending, processing, completed, failed)
            
        Returns:
            List of jobs with status, progress, timestamps
        """
        try:
            params = {'skip': skip, 'limit': limit}
            if status:
                params['status'] = status
            
            response = requests.get(
                f"{self.api_base}/jobs",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get jobs: {e}")
            raise
    
    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get status of a specific processing job.
        
        Args:
            job_id: Database ID of the job
            
        Returns:
            Job details including status, progress, logs, error messages
        """
        try:
            response = requests.get(
                f"{self.api_base}/jobs/{job_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            raise
    
    def trigger_processing(
        self,
        sample_ids: Optional[List[int]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger batch processing for samples.
        
        Args:
            sample_ids: List of specific sample IDs to process (None = all pending)
            force: Force reprocessing even if already completed
            
        Returns:
            Job creation confirmation with job_id
        """
        try:
            data = {'force': force}
            if sample_ids:
                data['sample_ids'] = sample_ids
            
            response = requests.post(
                f"{self.api_base}/process",
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Failed to trigger processing: {e}")
            raise


# ============================================================================
# Convenience Functions
# ============================================================================

def get_client(base_url: str = "http://localhost:8000") -> CRMITAPIClient:
    """
    Get API client instance.
    
    Args:
        base_url: Backend API URL
        
    Returns:
        Configured API client
    """
    return CRMITAPIClient(base_url=base_url)


def check_api_connection(base_url: str = "http://localhost:8000") -> bool:
    """
    Check if API is reachable.
    
    Args:
        base_url: Backend API URL
        
    Returns:
        True if API is responding, False otherwise
    """
    try:
        client = get_client(base_url)
        health = client.health_check()
        return health.get('status') == 'healthy'
    except Exception as e:
        logger.warning(f"⚠️ API not reachable: {e}")
        return False
