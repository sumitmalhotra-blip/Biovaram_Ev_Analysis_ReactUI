"""
Samples Query Router
====================

Endpoints for querying sample data.

Endpoints:
- GET /samples           - List all samples with optional filters
- GET /samples/{id}      - Get specific sample details
- GET /samples/{id}/fcs  - Get FCS results for sample
- GET /samples/{id}/nta  - Get NTA results for sample
- DELETE /samples/{id}   - Delete sample and all related data

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from typing import Optional, List, Dict, Any  # noqa: F401
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-not-found]
from sqlalchemy import select, func  # type: ignore[import-not-found]
from loguru import logger

from src.database.connection import get_session
from src.database.models import Sample, FCSResult, NTAResult, QCReport, ProcessingJob  # type: ignore[import-not-found]

router = APIRouter()


# ============================================================================
# Multi-Solution Mie Helper Functions
# ============================================================================

def detect_multi_solution_channels(channels: List[str]) -> Dict[str, Optional[str]]:
    """
    Detect VSSC (Violet SSC 405nm) and BSSC (Blue SSC 488nm) channels for multi-solution Mie.
    
    Returns dict with keys: 'vssc_channel', 'bssc_channel', 'can_use_multi_solution'
    """
    vssc_channel = None
    bssc_channel = None
    
    for ch in channels:
        ch_upper = ch.upper()
        # Detect VSSC (Violet SSC at 405nm) - prefer -H over -A
        if 'VSSC' in ch_upper and '-H' in ch_upper:
            if vssc_channel is None or 'VSSC1' in ch_upper:  # Prefer VSSC1-H
                vssc_channel = ch
        # Detect BSSC (Blue SSC at 488nm)
        if 'BSSC' in ch_upper and '-H' in ch_upper:
            bssc_channel = ch
    
    can_use_multi_solution = vssc_channel is not None and bssc_channel is not None
    
    return {
        'vssc_channel': vssc_channel,
        'bssc_channel': bssc_channel,
        'can_use_multi_solution': can_use_multi_solution
    }


# ============================================================================
# List Samples Endpoint
# ============================================================================

@router.get("/", response_model=dict)
async def list_samples(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    treatment: Optional[str] = Query(None, description="Filter by treatment"),
    qc_status: Optional[str] = Query(None, description="Filter by QC status (pass/warn/fail)"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (for user-specific samples)"),
    db: AsyncSession = Depends(get_session)
):
    """
    List all samples with optional filters.
    
    **Query Parameters:**
    - skip: Pagination offset (default: 0)
    - limit: Number of results (default: 100, max: 1000)
    - treatment: Filter by treatment (e.g., "CD81", "ISO")
    - qc_status: Filter by QC status ("pass", "warn", "fail")
    - processing_status: Filter by processing status ("pending", "completed", "failed")
    
    **Response:**
    ```json
    {
        "total": 150,
        "skip": 0,
        "limit": 100,
        "samples": [
            {
                "id": 1,
                "sample_id": "P5_F10_CD81",
                "treatment": "CD81",
                "qc_status": "pass",
                "processing_status": "completed",
                "upload_timestamp": "2025-11-21T12:00:00",
                "has_fcs": true,
                "has_nta": true,
                "has_tem": false
            },
            ...
        ]
    }
    ```
    """
    try:
        # Build query
        query = select(Sample)
        
        # Apply filters
        if user_id is not None:
            query = query.where(Sample.user_id == user_id)
        if treatment:
            query = query.where(Sample.treatment == treatment)
        if qc_status:
            query = query.where(Sample.qc_status == qc_status)
        if processing_status:
            query = query.where(Sample.processing_status == processing_status)
        
        # Get total count
        count_query = select(func.count()).select_from(Sample)
        if user_id is not None:
            count_query = count_query.where(Sample.user_id == user_id)
        if treatment:
            count_query = count_query.where(Sample.treatment == treatment)
        if qc_status:
            count_query = count_query.where(Sample.qc_status == qc_status)
        if processing_status:
            count_query = count_query.where(Sample.processing_status == processing_status)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        samples = result.scalars().all()
        
        # Format response
        samples_data = []
        for sample in samples:
            upload_ts = getattr(sample, 'upload_timestamp', None)
            samples_data.append({
                "id": sample.id,
                "sample_id": sample.sample_id,
                "biological_sample_id": sample.biological_sample_id,
                "treatment": sample.treatment,
                "qc_status": sample.qc_status,
                "processing_status": sample.processing_status,
                "upload_timestamp": upload_ts.isoformat() if upload_ts else None,
                "has_fcs": sample.file_path_fcs is not None,
                "has_nta": sample.file_path_nta is not None,
                "has_tem": sample.file_path_tem is not None,
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "samples": samples_data
        }
        
    except Exception as e:
        logger.exception(f"❌ Failed to list samples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list samples: {str(e)}"
        )


# ============================================================================
# Get Sample Details Endpoint
# ============================================================================

@router.get("/{sample_id}", response_model=dict)
async def get_sample(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get detailed information for a specific sample.
    
    **Path Parameters:**
    - sample_id: Sample identifier (e.g., "P5_F10_CD81")
    
    **Response:**
    ```json
    {
        "id": 1,
        "sample_id": "P5_F10_CD81",
        "biological_sample_id": "P5_F10",
        "treatment": "CD81",
        "concentration_ug": 1.0,
        "preparation_method": "SEC",
        "qc_status": "pass",
        "processing_status": "completed",
        "upload_timestamp": "2025-11-21T12:00:00",
        "files": {
            "fcs": "data/uploads/20251121_120000_file.fcs",
            "nta": "data/uploads/20251121_120100_file.txt",
            "tem": null
        },
        "results": {
            "fcs_count": 1,
            "nta_count": 1,
            "qc_reports_count": 2
        }
    }
    ```
    """
    try:
        # Query sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get related results counts
        fcs_query = select(func.count()).select_from(FCSResult).where(FCSResult.sample_id == sample.id)
        fcs_count = (await db.execute(fcs_query)).scalar()
        
        nta_query = select(func.count()).select_from(NTAResult).where(NTAResult.sample_id == sample.id)
        nta_count = (await db.execute(nta_query)).scalar()
        
        qc_query = select(func.count()).select_from(QCReport).where(QCReport.sample_id == sample.id)
        qc_count = (await db.execute(qc_query)).scalar()
        
        upload_ts = getattr(sample, 'upload_timestamp', None)
        exp_date = getattr(sample, 'experiment_date', None)
        
        return {
            "id": sample.id,
            "sample_id": sample.sample_id,
            "biological_sample_id": sample.biological_sample_id,
            "treatment": sample.treatment,
            "concentration_ug": sample.concentration_ug,
            "preparation_method": sample.preparation_method,
            "passage_number": sample.passage_number,
            "fraction_number": sample.fraction_number,
            "qc_status": sample.qc_status,
            "processing_status": sample.processing_status,
            "operator": sample.operator,
            "notes": sample.notes,
            "upload_timestamp": upload_ts.isoformat() if upload_ts else None,
            "experiment_date": exp_date.isoformat() if exp_date else None,
            "files": {
                "fcs": sample.file_path_fcs,
                "nta": sample.file_path_nta,
                "tem": sample.file_path_tem,
            },
            "results": {
                "fcs_count": fcs_count,
                "nta_count": nta_count,
                "qc_reports_count": qc_count,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get sample {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sample: {str(e)}"
        )


# ============================================================================
# Get FCS Results Endpoint
# ============================================================================

@router.get("/{sample_id}/fcs", response_model=dict)
async def get_fcs_results(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS analysis results for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "results": [
            {
                "id": 1,
                "total_events": 50000,
                "fsc_median": 15000,
                "ssc_median": 8000,
                "particle_size_median_nm": 82.5,
                "cd81_positive_pct": 45.2,
                "debris_pct": 5.3,
                "processed_at": "2025-11-21T12:05:00"
            }
        ]
    }
    ```
    """
    try:
        # Get sample
        sample_query = select(Sample).where(Sample.sample_id == sample_id)
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get FCS results
        fcs_query = select(FCSResult).where(FCSResult.sample_id == sample.id)
        fcs_result = await db.execute(fcs_query)
        fcs_results = fcs_result.scalars().all()
        
        results_data = []
        for fcs in fcs_results:
            processed = getattr(fcs, 'processed_at', None)
            results_data.append({
                "id": fcs.id,
                "total_events": fcs.total_events,
                "fsc_mean": fcs.fsc_mean,
                "fsc_median": fcs.fsc_median,
                "ssc_mean": fcs.ssc_mean,
                "ssc_median": fcs.ssc_median,
                "particle_size_mean_nm": fcs.particle_size_mean_nm,
                "particle_size_median_nm": fcs.particle_size_median_nm,
                "cd9_positive_pct": fcs.cd9_positive_pct,
                "cd81_positive_pct": fcs.cd81_positive_pct,
                "cd63_positive_pct": fcs.cd63_positive_pct,
                "debris_pct": fcs.debris_pct,
                "doublets_pct": fcs.doublets_pct,
                "processed_at": processed.isoformat() if processed else None,
                "parquet_file": fcs.parquet_file_path,
            })
        
        return {
            "sample_id": sample_id,
            "results": results_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS results for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS results: {str(e)}"
        )


# ============================================================================
# Get NTA Results Endpoint
# ============================================================================

@router.get("/{sample_id}/nta", response_model=dict)
async def get_nta_results(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA analysis results for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "results": [
            {
                "id": 1,
                "mean_size_nm": 85.3,
                "median_size_nm": 82.1,
                "d10_nm": 65.2,
                "d90_nm": 105.3,
                "concentration_particles_ml": 1.5e11,
                "temperature_celsius": 22.5,
                "processed_at": "2025-11-21T12:10:00"
            }
        ]
    }
    ```
    """
    try:
        # Get sample
        sample_query = select(Sample).where(Sample.sample_id == sample_id)
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get NTA results
        nta_query = select(NTAResult).where(NTAResult.sample_id == sample.id)
        nta_result = await db.execute(nta_query)
        nta_results = nta_result.scalars().all()
        
        results_data = []
        for nta in nta_results:
            processed = getattr(nta, 'processed_at', None)
            results_data.append({
                "id": nta.id,
                "mean_size_nm": nta.mean_size_nm,
                "median_size_nm": nta.median_size_nm,
                "d10_nm": nta.d10_nm,
                "d50_nm": nta.d50_nm,
                "d90_nm": nta.d90_nm,
                "concentration_particles_ml": nta.concentration_particles_ml,
                "temperature_celsius": nta.temperature_celsius,
                "ph": nta.ph,
                "bin_50_80nm_pct": nta.bin_50_80nm_pct,
                "bin_80_100nm_pct": nta.bin_80_100nm_pct,
                "bin_100_120nm_pct": nta.bin_100_120nm_pct,
                "processed_at": processed.isoformat() if processed else None,
                "parquet_file": nta.parquet_file_path,
            })
        
        return {
            "sample_id": sample_id,
            "results": results_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA results for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA results: {str(e)}"
        )


# ============================================================================
# Delete Sample Endpoint
# ============================================================================

@router.delete("/{sample_id}", response_model=dict)
async def delete_sample(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Delete a sample and all related data.
    
    **WARNING:** This will permanently delete:
    - Sample record
    - All FCS results
    - All NTA results
    - All QC reports
    - All processing jobs
    - Audit log will record deletion
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Sample P5_F10_CD81 deleted successfully",
        "deleted_records": {
            "fcs_results": 1,
            "nta_results": 1,
            "qc_reports": 2,
            "processing_jobs": 3
        }
    }
    ```
    """
    try:
        # Get sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Count related records (for response)
        fcs_count = (await db.execute(
            select(func.count()).select_from(FCSResult).where(FCSResult.sample_id == sample.id)
        )).scalar()
        
        nta_count = (await db.execute(
            select(func.count()).select_from(NTAResult).where(NTAResult.sample_id == sample.id)
        )).scalar()
        
        qc_count = (await db.execute(
            select(func.count()).select_from(QCReport).where(QCReport.sample_id == sample.id)
        )).scalar()
        
        job_count = (await db.execute(
            select(func.count()).select_from(ProcessingJob).where(ProcessingJob.sample_id == sample.id)
        )).scalar()
        
        # Delete sample (cascade will delete related records)
        await db.delete(sample)
        await db.commit()
        
        logger.warning(f"🗑️  Deleted sample: {sample_id} (FCS: {fcs_count}, NTA: {nta_count}, QC: {qc_count}, Jobs: {job_count})")
        
        return {
            "success": True,
            "message": f"Sample {sample_id} deleted successfully",
            "deleted_records": {
                "fcs_results": fcs_count,
                "nta_results": nta_count,
                "qc_reports": qc_count,
                "processing_jobs": job_count,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to delete sample {sample_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sample: {str(e)}"
        )


# ============================================================================
# Scatter Data Endpoint
# ============================================================================

@router.get("/{sample_id}/scatter-data", response_model=dict)
async def get_scatter_data(
    sample_id: str,
    max_points: int = Query(5000, ge=100, le=100000, description="Maximum points to return"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override (e.g., 'Channel_4')"),
    wavelength_nm: float = Query(488.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.40, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get FSC/SSC scatter plot data for a sample.
    
    Returns actual event-level FSC and SSC values for visualization.
    Samples data if event count exceeds max_points for performance.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "total_events": 100000,
        "returned_points": 5000,
        "data": [
            {"x": 250000, "y": 150000, "index": 0},
            ...
        ],
        "channels": {
            "fsc": "FSC-A",
            "ssc": "SSC-A"
        }
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file to get scatter data
        from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        import pandas as pd
        import numpy as np
        
        logger.info(f"📊 Loading scatter data for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Get available channels
        channels = parser.channel_names
        
        # Get channel configuration
        channel_config = get_channel_config()
        
        # Use override if provided, otherwise use config-based detection
        fsc_ch = fsc_channel  # From query parameter
        ssc_ch = ssc_channel  # From query parameter
        
        # Validate override channels exist - fallback if not found
        if fsc_ch and fsc_ch not in channels:
            logger.warning(f"⚠️ Requested FSC channel '{fsc_ch}' not found, will auto-detect")
            fsc_ch = None  # Reset to trigger auto-detection
        if ssc_ch and ssc_ch not in channels:
            logger.warning(f"⚠️ Requested SSC channel '{ssc_ch}' not found, will auto-detect")
            ssc_ch = None  # Reset to trigger auto-detection
        
        # Use channel config for detection if not overridden
        if not fsc_ch:
            fsc_ch = channel_config.detect_fsc_channel(channels)
        
        if not ssc_ch:
            ssc_ch = channel_config.detect_ssc_channel(channels)
        
        # Fallback: Use first two channels if detection fails
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
            logger.warning(f"⚠️ FSC channel not found, using first channel: {fsc_ch}")
        
        if not ssc_ch and len(channels) >= 2:
            ssc_ch = channels[1]
            logger.warning(f"⚠️ SSC channel not found, using second channel: {ssc_ch}")
        
        if not fsc_ch or not ssc_ch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find FSC/SSC channels in FCS file. Available: {', '.join(channels)}"
            )
        
        # Extract FSC and SSC data
        total_events = len(parsed_data)
        
        # Sample data if too many points
        if total_events > max_points:
            # Use random sampling to maintain distribution
            sampled_indices = np.random.choice(total_events, size=max_points, replace=False)
            sampled_indices.sort()
            sampled_data = parsed_data.iloc[sampled_indices].reset_index(drop=True)
            logger.info(f"📉 Sampled {max_points} from {total_events} events")
        else:
            sampled_data = parsed_data.reset_index(drop=True)
            sampled_indices = np.arange(total_events)
        
        # Build scatter data array with diameter calculation
        # Note: Use direct column access instead of itertuples() to handle column names with hyphens
        fsc_values = sampled_data[fsc_ch].values
        ssc_values = sampled_data[ssc_ch].values
        
        # Check for multi-solution Mie capability (VSSC + BSSC channels)
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in sampled_data.columns and
            multi_solution_info['bssc_channel'] in sampled_data.columns
        )
        
        # Calculate diameters using appropriate method
        try:
            if can_use_multi_solution:
                # === MULTI-SOLUTION MIE (PREFERRED) ===
                from src.physics.mie_scatter import MultiSolutionMieCalculator
                
                vssc_ch = multi_solution_info['vssc_channel']
                bssc_ch = multi_solution_info['bssc_channel']
                
                logger.info(f"🔬 Using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
                
                multi_mie_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium)
                
                # Get SSC values for both wavelengths
                ssc_violet = np.asarray(sampled_data[vssc_ch].values, dtype=np.float64)
                ssc_blue = np.asarray(sampled_data[bssc_ch].values, dtype=np.float64)
                
                # Calculate sizes with disambiguation
                diameters, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
                success_mask = ~np.isnan(diameters) & (diameters > 0)
                valid_diameter_count = int(np.sum(success_mask))
                
                logger.info(f"📐 Multi-solution: {valid_diameter_count}/{len(ssc_blue)} valid diameters")
            else:
                # === SINGLE-SOLUTION MIE (FALLBACK) ===
                from src.physics.mie_scatter import MieScatterCalculator
                mie_calc = MieScatterCalculator(
                    wavelength_nm=wavelength_nm,
                    n_particle=n_particle,
                    n_medium=n_medium
                )
                logger.info(f"🔬 Using single-solution Mie: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
                
                # Use batch diameter calculation with normalization for performance
                diameters, success_mask = mie_calc.diameters_from_scatter_normalized(
                    fsc_intensities=fsc_values,
                    min_diameter=20.0,
                    max_diameter=500.0
                )
                valid_diameter_count = int(np.sum(success_mask))
                logger.info(f"📐 Single-solution: {valid_diameter_count}/{len(fsc_values)} valid diameters")
        except Exception as e:
            logger.warning(f"⚠️ Mie calculation failed, using fallback: {e}")
            # Fallback: use relative FSC mapping
            diameters = np.zeros(len(fsc_values))
            success_mask = np.zeros(len(fsc_values), dtype=bool)
            valid_diameter_count = 0
        
        scatter_data = []
        for idx, orig_idx in enumerate(sampled_indices):
            fsc_val = float(fsc_values[idx])
            ssc_val = float(ssc_values[idx])
            
            point_data = {
                "x": fsc_val,
                "y": ssc_val,
                "index": int(orig_idx)
            }
            
            # Add diameter if valid
            if success_mask[idx] and diameters[idx] > 0:
                point_data["diameter"] = round(float(diameters[idx]), 1)
            
            scatter_data.append(point_data)
        
        logger.success(f"✅ Returned {len(scatter_data)} scatter points ({valid_diameter_count} with diameter) for {sample_id}")
        
        return {
            "sample_id": sample_id,
            "total_events": total_events,
            "returned_points": len(scatter_data),
            "data": scatter_data,
            "channels": {
                "fsc": fsc_ch,
                "ssc": ssc_ch,
                "available": channels  # Include all available channels for UI
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get scatter data for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scatter data: {str(e)}"
        )


# ============================================================================
# Clustered Scatter Data Endpoint (UI-002: Large Dataset Visualization)
# ============================================================================

@router.get("/{sample_id}/clustered-scatter", response_model=dict)
async def get_clustered_scatter_data(
    sample_id: str,
    zoom_level: int = Query(1, ge=1, le=3, description="Zoom level: 1=overview (few clusters), 2=medium, 3=detailed"),
    n_clusters_base: int = Query(8, ge=3, le=20, description="Base number of clusters at zoom level 1"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override"),
    viewport_x_min: Optional[float] = Query(None, description="Viewport X minimum (for zoom level 3)"),
    viewport_x_max: Optional[float] = Query(None, description="Viewport X maximum (for zoom level 3)"),
    viewport_y_min: Optional[float] = Query(None, description="Viewport Y minimum (for zoom level 3)"),
    viewport_y_max: Optional[float] = Query(None, description="Viewport Y maximum (for zoom level 3)"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get hierarchical clustered scatter data for efficient large dataset visualization.
    
    This endpoint uses K-means clustering to summarize large datasets (900k+ events)
    into manageable clusters that can be rendered efficiently. As the user zooms in,
    more detail is revealed.
    
    **Zoom Levels:**
    - Level 1 (Overview): ~8-10 clusters showing major population groups
    - Level 2 (Medium): ~40-50 sub-clusters for more detail
    - Level 3 (Detailed): Individual points within viewport (max 2000)
    
    **Response:**
    ```json
    {
        "sample_id": "PC3_EXO1",
        "zoom_level": 1,
        "total_events": 900000,
        "clusters": [
            {
                "id": 0,
                "cx": 25000,
                "cy": 15000,
                "count": 45000,
                "radius": 30,
                "std_x": 5000,
                "std_y": 3000,
                "pct": 5.0,
                "avg_diameter": 95.2
            },
            ...
        ],
        "bounds": {"x_min": 0, "x_max": 262144, "y_min": 0, "y_max": 262144},
        "individual_points": null
    }
    ```
    
    **Performance:** 
    - Level 1-2: Returns clusters (fast, <100ms)
    - Level 3: Returns up to 2000 individual points within viewport
    """
    from sklearn.cluster import KMeans, MiniBatchKMeans
    import numpy as np
    
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.utils.channel_config import get_channel_config
        
        logger.info(f"📊 Loading clustered scatter data for {sample_id} at zoom level {zoom_level}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        channels = parser.channel_names
        
        # Detect channels
        channel_config = get_channel_config()
        fsc_ch = fsc_channel if fsc_channel and fsc_channel in channels else channel_config.detect_fsc_channel(channels)
        ssc_ch = ssc_channel if ssc_channel and ssc_channel in channels else channel_config.detect_ssc_channel(channels)
        
        if not fsc_ch or not ssc_ch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not detect FSC/SSC channels. Available: {channels}"
            )
        
        # Extract data
        fsc_values = parsed_data[fsc_ch].values.astype(np.float64)
        ssc_values = parsed_data[ssc_ch].values.astype(np.float64)
        total_events = len(fsc_values)
        
        # Calculate data bounds
        x_min, x_max = float(np.min(fsc_values)), float(np.max(fsc_values))
        y_min, y_max = float(np.min(ssc_values)), float(np.max(ssc_values))
        
        # Calculate diameters if possible (for cluster statistics)
        try:
            multi_solution_info = detect_multi_solution_channels(channels)
            if multi_solution_info['can_use_multi_solution']:
                from src.physics.mie_scatter import MultiSolutionMieCalculator
                vssc_ch = multi_solution_info['vssc_channel']
                bssc_ch = multi_solution_info['bssc_channel']
                calc = MultiSolutionMieCalculator(n_particle=1.40, n_medium=1.33)
                ssc_violet = parsed_data[vssc_ch].values.astype(np.float64)
                ssc_blue = parsed_data[bssc_ch].values.astype(np.float64)
                diameters, _ = calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            else:
                from src.physics.mie_scatter import MieScatterCalculator
                calc = MieScatterCalculator(wavelength_nm=488.0, n_particle=1.40, n_medium=1.33)
                diameters, _ = calc.diameters_from_scatter_normalized(fsc_values, min_diameter=20.0, max_diameter=500.0)
        except Exception as e:
            logger.warning(f"Could not calculate diameters: {e}")
            diameters = np.full(total_events, np.nan)
        
        # Determine number of clusters based on zoom level
        if zoom_level == 1:
            n_clusters = n_clusters_base
        elif zoom_level == 2:
            n_clusters = n_clusters_base * 5  # ~40 clusters
        else:
            # Level 3: Return individual points within viewport
            n_clusters = None
        
        if zoom_level < 3:
            # Use MiniBatchKMeans for large datasets (faster than regular KMeans)
            X = np.column_stack([fsc_values, ssc_values])
            
            # Sample for very large datasets to speed up clustering
            if total_events > 100000:
                sample_size = min(50000, total_events)
                sample_indices = np.random.choice(total_events, sample_size, replace=False)
                X_sample = X[sample_indices]
                diameters_sample = diameters[sample_indices]
            else:
                X_sample = X
                diameters_sample = diameters
                sample_indices = np.arange(total_events)
            
            # Perform clustering
            kmeans = MiniBatchKMeans(
                n_clusters=n_clusters,
                random_state=42,
                batch_size=1024,
                n_init=3
            )
            labels = kmeans.fit_predict(X_sample)
            
            # Build cluster data
            clusters = []
            for i in range(n_clusters):
                mask = labels == i
                cluster_points = X_sample[mask]
                cluster_diameters = diameters_sample[mask]
                
                if len(cluster_points) == 0:
                    continue
                
                # Calculate cluster statistics
                cx = float(np.mean(cluster_points[:, 0]))
                cy = float(np.mean(cluster_points[:, 1]))
                std_x = float(np.std(cluster_points[:, 0]))
                std_y = float(np.std(cluster_points[:, 1]))
                count = int(np.sum(mask))
                
                # Scale count back to full dataset if we sampled
                if total_events > 100000:
                    count = int(count * (total_events / len(sample_indices)))
                
                pct = round(count / total_events * 100, 2)
                
                # Calculate radius based on count (log scale for visual balance)
                # Min radius 8, max radius 50
                radius = max(8, min(50, 8 + 10 * np.log10(max(1, count / 100))))
                
                # Average diameter for cluster
                valid_diameters = cluster_diameters[~np.isnan(cluster_diameters)]
                avg_diameter = float(np.mean(valid_diameters)) if len(valid_diameters) > 0 else None
                
                clusters.append({
                    "id": i,
                    "cx": round(cx, 2),
                    "cy": round(cy, 2),
                    "count": count,
                    "radius": round(radius, 1),
                    "std_x": round(std_x, 2),
                    "std_y": round(std_y, 2),
                    "pct": pct,
                    "avg_diameter": round(avg_diameter, 1) if avg_diameter else None
                })
            
            # Sort by count descending
            clusters.sort(key=lambda c: c["count"], reverse=True)
            
            logger.success(f"✅ Generated {len(clusters)} clusters for {sample_id} at zoom level {zoom_level}")
            
            return {
                "sample_id": sample_id,
                "zoom_level": zoom_level,
                "total_events": total_events,
                "clusters": clusters,
                "bounds": {
                    "x_min": round(x_min, 2),
                    "x_max": round(x_max, 2),
                    "y_min": round(y_min, 2),
                    "y_max": round(y_max, 2)
                },
                "channels": {"fsc": fsc_ch, "ssc": ssc_ch},
                "individual_points": None
            }
        
        else:
            # Zoom level 3: Return individual points within viewport
            if viewport_x_min is None:
                viewport_x_min = x_min
            if viewport_x_max is None:
                viewport_x_max = x_max
            if viewport_y_min is None:
                viewport_y_min = y_min
            if viewport_y_max is None:
                viewport_y_max = y_max
            
            # Filter points within viewport
            mask = (
                (fsc_values >= viewport_x_min) & (fsc_values <= viewport_x_max) &
                (ssc_values >= viewport_y_min) & (ssc_values <= viewport_y_max)
            )
            
            viewport_indices = np.where(mask)[0]
            
            # Limit to 2000 points
            max_points = 2000
            if len(viewport_indices) > max_points:
                viewport_indices = np.random.choice(viewport_indices, max_points, replace=False)
            
            # Build individual points
            points = []
            for idx in viewport_indices:
                point = {
                    "x": float(fsc_values[idx]),
                    "y": float(ssc_values[idx]),
                    "index": int(idx)
                }
                if not np.isnan(diameters[idx]):
                    point["diameter"] = round(float(diameters[idx]), 1)
                points.append(point)
            
            logger.success(f"✅ Returned {len(points)} individual points for {sample_id} at zoom level 3")
            
            return {
                "sample_id": sample_id,
                "zoom_level": zoom_level,
                "total_events": total_events,
                "clusters": None,
                "bounds": {
                    "x_min": round(x_min, 2),
                    "x_max": round(x_max, 2),
                    "y_min": round(y_min, 2),
                    "y_max": round(y_max, 2)
                },
                "viewport": {
                    "x_min": viewport_x_min,
                    "x_max": viewport_x_max,
                    "y_min": viewport_y_min,
                    "y_max": viewport_y_max
                },
                "channels": {"fsc": fsc_ch, "ssc": ssc_ch},
                "individual_points": points,
                "points_in_viewport": len(viewport_indices) if len(viewport_indices) <= max_points else f"{len(viewport_indices)} (sampled to {max_points})"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get clustered scatter data for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clustered scatter data: {str(e)}"
        )


# ============================================================================
# Gated Analysis Endpoint (T-009: Population Gating)
# ============================================================================

from pydantic import BaseModel, Field
from typing import Literal

class RectangleGateRequest(BaseModel):
    """Rectangle gate coordinates."""
    type: Literal["rectangle"] = "rectangle"
    x1: float = Field(..., description="Left X coordinate")
    y1: float = Field(..., description="Bottom Y coordinate")
    x2: float = Field(..., description="Right X coordinate")
    y2: float = Field(..., description="Top Y coordinate")


class PolygonGateRequest(BaseModel):
    """Polygon gate coordinates."""
    type: Literal["polygon"] = "polygon"
    points: List[Dict[str, float]] = Field(..., description="List of {x, y} points defining polygon vertices")


class EllipseGateRequest(BaseModel):
    """Ellipse gate coordinates."""
    type: Literal["ellipse"] = "ellipse"
    cx: float = Field(..., description="Center X coordinate")
    cy: float = Field(..., description="Center Y coordinate")
    rx: float = Field(..., description="X radius")
    ry: float = Field(..., description="Y radius")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees")


class GatedAnalysisRequest(BaseModel):
    """Request model for gated population analysis."""
    gate_name: str = Field(default="Gate 1", description="Name of the gate")
    gate_type: Literal["rectangle", "polygon", "ellipse"] = Field(default="rectangle", description="Gate shape type")
    gate_coordinates: Dict[str, Any] = Field(..., description="Gate coordinates based on type")
    x_channel: str = Field(..., description="X-axis channel name")
    y_channel: str = Field(..., description="Y-axis channel name")
    include_diameter_stats: bool = Field(default=True, description="Include diameter statistics")
    # Mie parameters for size calculations
    wavelength_nm: float = Field(default=488.0, ge=200, le=800, description="Laser wavelength")
    n_particle: float = Field(default=1.40, ge=1.0, le=2.0, description="Particle refractive index")
    n_medium: float = Field(default=1.33, ge=1.0, le=2.0, description="Medium refractive index")


@router.post("/{sample_id}/gated-analysis", response_model=dict)
async def analyze_gated_population(
    sample_id: str,
    request: GatedAnalysisRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Analyze a gated (selected) population from a scatter plot.
    
    This endpoint performs statistical analysis on a subset of events
    that fall within a user-defined gate region on a scatter plot.
    
    **Supported Gate Types:**
    - Rectangle: `{x1, y1, x2, y2}` - axis-aligned bounding box
    - Polygon: `{points: [{x, y}, ...]}` - arbitrary polygon vertices
    - Ellipse: `{cx, cy, rx, ry, rotation}` - rotated ellipse
    
    **Request Example:**
    ```json
    {
        "gate_name": "EV Population",
        "gate_type": "rectangle",
        "gate_coordinates": {"x1": 100, "y1": 200, "x2": 500, "y2": 800},
        "x_channel": "FSC-A",
        "y_channel": "SSC-A",
        "include_diameter_stats": true
    }
    ```
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "gate_name": "EV Population",
        "total_events": 100000,
        "gated_events": 24500,
        "gated_percentage": 24.5,
        "statistics": {
            "x_channel": {
                "channel": "FSC-A",
                "mean": 350.2,
                "median": 320.5,
                "std": 125.3,
                "min": 100.0,
                "max": 500.0,
                "cv": 35.8
            },
            "y_channel": {...},
            "diameter": {...}
        },
        "percentiles": {
            "D10": 85.2,
            "D50": 120.5,
            "D90": 185.3
        },
        "comparison_to_total": {
            "x_mean_diff_percent": -12.5,
            "y_mean_diff_percent": 8.2,
            "enrichment_factor": 1.85
        }
    }
    ```
    """
    import numpy as np
    
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.utils.channel_config import get_channel_config
        
        logger.info(f"🎯 Running gated analysis for sample: {sample_id}, gate: {request.gate_name}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Validate channels exist
        available_channels = list(parsed_data.columns)
        if request.x_channel not in available_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"X channel '{request.x_channel}' not found. Available: {available_channels}"
            )
        if request.y_channel not in available_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Y channel '{request.y_channel}' not found. Available: {available_channels}"
            )
        
        # Extract channel data
        x_data = parsed_data[request.x_channel].values
        y_data = parsed_data[request.y_channel].values
        total_events = len(x_data)
        
        # Apply gate to find selected points
        gate_coords = request.gate_coordinates
        gate_type = request.gate_type
        
        if gate_type == "rectangle":
            # Rectangle gate: check if points are within bounds
            x1, y1 = gate_coords.get("x1", 0), gate_coords.get("y1", 0)
            x2, y2 = gate_coords.get("x2", 0), gate_coords.get("y2", 0)
            
            # Ensure correct ordering
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)
            
            mask = (
                (x_data >= x_min) & (x_data <= x_max) &
                (y_data >= y_min) & (y_data <= y_max)
            )
            
        elif gate_type == "polygon":
            # Polygon gate: point-in-polygon test
            points = gate_coords.get("points", [])
            if len(points) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Polygon gate requires at least 3 points"
                )
            
            # Use matplotlib path for efficient point-in-polygon
            try:
                from matplotlib.path import Path
                polygon_vertices = [(p["x"], p["y"]) for p in points]
                polygon_path = Path(polygon_vertices)
                test_points = np.column_stack((x_data, y_data))
                mask = polygon_path.contains_points(test_points)
            except ImportError:
                # Fallback: simple ray casting algorithm
                mask = np.array([
                    _point_in_polygon(x_data[i], y_data[i], points)
                    for i in range(len(x_data))
                ])
                
        elif gate_type == "ellipse":
            # Ellipse gate: check if points are within ellipse
            cx = gate_coords.get("cx", 0)
            cy = gate_coords.get("cy", 0)
            rx = gate_coords.get("rx", 1)
            ry = gate_coords.get("ry", 1)
            rotation = np.radians(gate_coords.get("rotation", 0))
            
            # Transform points relative to ellipse center
            dx = x_data - cx
            dy = y_data - cy
            
            # Apply rotation
            cos_r, sin_r = np.cos(-rotation), np.sin(-rotation)
            rx_rot = dx * cos_r - dy * sin_r
            ry_rot = dx * sin_r + dy * cos_r
            
            # Check if within ellipse
            mask = ((rx_rot / rx) ** 2 + (ry_rot / ry) ** 2) <= 1.0
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported gate type: {gate_type}"
            )
        
        # Get gated data
        gated_indices = np.where(mask)[0]
        gated_count = len(gated_indices)
        gated_percentage = (gated_count / total_events * 100) if total_events > 0 else 0
        
        if gated_count == 0:
            return {
                "sample_id": sample_id,
                "gate_name": request.gate_name,
                "gate_type": gate_type,
                "total_events": total_events,
                "gated_events": 0,
                "gated_percentage": 0.0,
                "message": "No events found within the gate region",
                "statistics": None,
                "percentiles": None,
                "comparison_to_total": None
            }
        
        # Get gated values
        gated_x = x_data[mask]
        gated_y = y_data[mask]
        
        # Calculate statistics helper function
        def calc_stats(values: np.ndarray, channel_name: str) -> dict:
            """Calculate comprehensive statistics for a channel."""
            return {
                "channel": channel_name,
                "count": len(values),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "cv": float(np.std(values) / np.mean(values) * 100) if np.mean(values) > 0 else 0,
                "q25": float(np.percentile(values, 25)),
                "q75": float(np.percentile(values, 75)),
                "iqr": float(np.percentile(values, 75) - np.percentile(values, 25))
            }
        
        # Calculate gated statistics
        x_stats = calc_stats(gated_x, request.x_channel)
        y_stats = calc_stats(gated_y, request.y_channel)
        
        # Calculate total population statistics for comparison
        total_x_mean = float(np.mean(x_data))
        total_y_mean = float(np.mean(y_data))
        
        # Diameter statistics if requested
        diameter_stats = None
        diameter_percentiles = None
        
        if request.include_diameter_stats:
            try:
                # Check for multi-solution Mie capability
                multi_solution_info = detect_multi_solution_channels(available_channels)
                can_use_multi_solution = (
                    multi_solution_info['can_use_multi_solution'] and
                    multi_solution_info['vssc_channel'] in parsed_data.columns and
                    multi_solution_info['bssc_channel'] in parsed_data.columns
                )
                
                if can_use_multi_solution:
                    # === MULTI-SOLUTION MIE (PREFERRED) ===
                    from src.physics.mie_scatter import MultiSolutionMieCalculator
                    
                    vssc_ch = multi_solution_info['vssc_channel']
                    bssc_ch = multi_solution_info['bssc_channel']
                    
                    logger.info(f"🔬 Gated analysis using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
                    
                    multi_mie_calc = MultiSolutionMieCalculator(
                        n_particle=request.n_particle, 
                        n_medium=request.n_medium
                    )
                    
                    # Get SSC values for gated events
                    gated_vssc = np.asarray(parsed_data[vssc_ch].values[mask], dtype=np.float64)
                    gated_bssc = np.asarray(parsed_data[bssc_ch].values[mask], dtype=np.float64)
                    
                    # Calculate sizes with disambiguation
                    sizes, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(gated_bssc, gated_vssc)
                    diameters = sizes[~np.isnan(sizes) & (sizes > 0)]
                else:
                    # === SINGLE-SOLUTION MIE (FALLBACK) ===
                    from src.physics.mie_scatter import MieScatterCalculator
                    mie_calc = MieScatterCalculator(
                        wavelength_nm=request.wavelength_nm,
                        n_particle=request.n_particle,
                        n_medium=request.n_medium
                    )
                    logger.info(f"🔬 Gated analysis using single-solution Mie: λ={request.wavelength_nm}nm")
                    
                    # Calculate diameters for gated events
                    diameters = []
                    for fsc_val in gated_x:
                        try:
                            d, success = mie_calc.diameter_from_scatter(
                                fsc_intensity=float(fsc_val),
                                min_diameter=20.0,
                                max_diameter=500.0
                            )
                            if success and d > 0:
                                diameters.append(d)
                        except Exception:
                            pass
                    diameters = np.array(diameters) if diameters else np.array([])
                
                if len(diameters) >= 10:  # Need enough data points
                    diameter_stats = calc_stats(diameters, "diameter_nm")
                    diameter_percentiles = {
                        "D10": float(np.percentile(diameters, 10)),
                        "D50": float(np.percentile(diameters, 50)),
                        "D90": float(np.percentile(diameters, 90)),
                        "mean": float(np.mean(diameters)),
                        "mode_estimate": float(np.percentile(diameters, 50))  # Using median as mode estimate
                    }
                    logger.info(f"📏 Calculated diameter for {len(diameters)}/{gated_count} gated events")
            except Exception as e:
                logger.warning(f"⚠️ Failed to calculate diameter stats: {e}")
        
        # Calculate comparison metrics
        comparison = {
            "x_mean_diff_percent": float((x_stats["mean"] - total_x_mean) / total_x_mean * 100) if total_x_mean != 0 else 0,
            "y_mean_diff_percent": float((y_stats["mean"] - total_y_mean) / total_y_mean * 100) if total_y_mean != 0 else 0,
            "enrichment_factor": gated_percentage / 100.0 * total_events / gated_count if gated_count > 0 else 0,
            "total_x_mean": total_x_mean,
            "total_y_mean": total_y_mean,
            "total_x_std": float(np.std(x_data)),
            "total_y_std": float(np.std(y_data))
        }
        
        logger.success(f"✅ Gated analysis complete: {gated_count}/{total_events} events ({gated_percentage:.2f}%)")
        
        return {
            "sample_id": sample_id,
            "gate_name": request.gate_name,
            "gate_type": gate_type,
            "gate_coordinates": gate_coords,
            "total_events": total_events,
            "gated_events": gated_count,
            "gated_percentage": round(gated_percentage, 2),
            "gated_indices": gated_indices.tolist()[:1000],  # Return first 1000 indices for reference
            "statistics": {
                "x_channel": x_stats,
                "y_channel": y_stats,
                "diameter": diameter_stats
            },
            "percentiles": diameter_percentiles,
            "comparison_to_total": comparison
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed gated analysis for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze gated population: {str(e)}"
        )


def _point_in_polygon(x: float, y: float, polygon: List[Dict[str, float]]) -> bool:
    """
    Ray casting algorithm for point-in-polygon test.
    Fallback when matplotlib is not available.
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]["x"], polygon[i]["y"]
        xj, yj = polygon[j]["x"], polygon[j]["y"]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


# ============================================================================
# Auto Axis Selection Endpoint (CRMIT-002)
# ============================================================================

@router.get("/{sample_id}/recommend-axes", response_model=dict)
async def get_recommended_axes(
    sample_id: str,
    n_recommendations: int = Query(5, ge=1, le=10, description="Number of axis pair recommendations"),
    include_scatter: bool = Query(True, description="Include scatter channel combinations"),
    include_fluorescence: bool = Query(True, description="Include fluorescence channel combinations"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get AI-recommended optimal axis pairs for scatter plot visualization.
    
    Uses intelligent analysis to recommend the best channel combinations based on:
    - Variance and spread (information content)
    - Correlation between channels (avoid redundancy)
    - Dynamic range assessment
    - Population separation metrics (multi-modal distributions)
    - Standard cytometry best practices
    
    **Scoring Criteria:**
    - Variance (30%): High variance = more information
    - Correlation (20%): Low correlation = independent information
    - Dynamic Range (20%): Larger range = better separation
    - Population Separation (20%): Multi-population = interesting biology
    - Modality (10%): Bimodal distributions = distinct populations
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "recommendations": [
            {
                "rank": 1,
                "x_channel": "VFSC-A",
                "y_channel": "VSSC1-A",
                "score": 0.95,
                "reason": "Standard gating view (FSC vs SSC)",
                "description": "Universal starting point for flow cytometry. Used for initial gating, doublet discrimination, and debris removal."
            },
            {
                "rank": 2,
                "x_channel": "B531-H",
                "y_channel": "VFSC-A",
                "score": 0.78,
                "reason": "Fluorescence vs Size",
                "description": "Compare marker expression with particle size to identify marker-positive populations."
            }
        ],
        "channels": {
            "scatter": ["VFSC-A", "VFSC-H", "VSSC1-A", "VSSC1-H"],
            "fluorescence": ["B531-H", "R670-H", "Y585-H", "V447-H"],
            "all": ["VFSC-A", "VFSC-H", "VSSC1-A", ...]
        }
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.visualization.auto_axis_selector import AutoAxisSelector
        
        logger.info(f"🎯 Analyzing optimal axes for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Get all available channels
        all_channels = parser.channel_names
        
        # Initialize auto-axis selector
        selector = AutoAxisSelector()
        
        # Get channel categories
        scatter_channels = selector._identify_scatter_channels(all_channels)
        fluorescence_channels = selector._identify_fluorescence_channels(all_channels)
        
        # Get recommendations
        best_pairs = selector.select_best_axes(
            parsed_data,
            n_pairs=n_recommendations,
            include_scatter=include_scatter,
            include_fluorescence=include_fluorescence
        )
        
        # Build detailed recommendations
        recommendations = []
        for rank, (x_ch, y_ch, score) in enumerate(best_pairs, 1):
            # Determine reason and description
            x_upper = x_ch.upper()
            y_upper = y_ch.upper()
            
            # Check channel types
            x_is_scatter = any(s in x_upper for s in ['FSC', 'SSC', 'VFSC', 'VSSC'])
            y_is_scatter = any(s in y_upper for s in ['FSC', 'SSC', 'VFSC', 'VSSC'])
            
            if x_is_scatter and y_is_scatter:
                # Both scatter - check if FSC vs SSC
                is_fsc_ssc = (
                    ('FSC' in x_upper or 'VFSC' in x_upper) and 
                    ('SSC' in y_upper or 'VSSC' in y_upper)
                ) or (
                    ('SSC' in x_upper or 'VSSC' in x_upper) and 
                    ('FSC' in y_upper or 'VFSC' in y_upper)
                )
                if is_fsc_ssc:
                    reason = "Standard gating view (FSC vs SSC)"
                    description = "Universal starting point for flow cytometry. Used for initial gating, doublet discrimination, and debris removal."
                else:
                    reason = "Scatter comparison"
                    description = "Compare scatter parameters to identify particle characteristics (e.g., FSC-A vs FSC-H for doublet discrimination)."
            elif x_is_scatter or y_is_scatter:
                reason = "Fluorescence vs Size"
                description = "Compare marker expression with particle size to identify size characteristics of marker-positive populations."
            else:
                reason = "Multi-marker analysis"
                description = "Compare expression of two fluorescence markers to identify co-expression patterns and distinct populations."
            
            recommendations.append({
                "rank": rank,
                "x_channel": x_ch,
                "y_channel": y_ch,
                "score": round(float(score), 3),
                "reason": reason,
                "description": description
            })
        
        logger.success(f"✅ Generated {len(recommendations)} axis recommendations for {sample_id}")
        
        return {
            "sample_id": sample_id,
            "total_events": len(parsed_data),
            "recommendations": recommendations,
            "channels": {
                "scatter": scatter_channels,
                "fluorescence": fluorescence_channels,
                "all": all_channels
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get axis recommendations for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get axis recommendations: {str(e)}"
        )


# ============================================================================
# Particle Size Binning Endpoint
# ============================================================================

@router.get("/{sample_id}/size-bins", response_model=dict)
async def get_size_bins(
    sample_id: str,
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    wavelength_nm: float = Query(488.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.40, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get particle size distribution binned into small/medium/large categories.
    
    Uses Mie scattering theory to convert FSC values to particle sizes,
    then bins into standard EV size categories.
    
    **Size Categories:**
    - Small: < 50 nm (exomeres, small EVs)
    - Medium: 50-200 nm (exosomes, classic EVs)
    - Large: > 200 nm (microvesicles, large EVs)
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "total_events": 100000,
        "bins": {
            "small": 15000,
            "medium": 70000,
            "large": 15000
        },
        "percentages": {
            "small": 15.0,
            "medium": 70.0,
            "large": 15.0
        }
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file and calculate sizes
        from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]
        import numpy as np
        
        logger.info(f"📏 Calculating size bins for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Get available channels
        channels = parser.channel_names
        
        # Get channel configuration
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        channel_config = get_channel_config()
        
        # Use override if provided
        fsc_ch = fsc_channel  # From query parameter
        
        # Validate override channel exists
        if fsc_ch and fsc_ch not in channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FSC channel '{fsc_ch}' not found. Available: {', '.join(channels)}"
            )
        
        # Use channel config for detection if not overridden
        if not fsc_ch:
            fsc_ch = channel_config.detect_fsc_channel(channels)
        
        # Fallback: Use first channel if detection fails
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
            logger.warning(f"⚠️ FSC channel not found for size bins, using first channel: {fsc_ch}")
        
        total_events = len(parsed_data)
        
        # Sample for performance (calculate on subset, extrapolate to full dataset)
        sample_size = min(10000, total_events)
        np.random.seed(42)
        sample_indices = np.random.choice(total_events, size=sample_size, replace=False) if total_events > sample_size else np.arange(total_events)
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in parsed_data.columns and
            multi_solution_info['bssc_channel'] in parsed_data.columns
        )
        
        if can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 Size bins using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            multi_mie_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(parsed_data[vssc_ch].values[sample_indices], dtype=np.float64)
            ssc_blue = np.asarray(parsed_data[bssc_ch].values[sample_indices], dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes_array, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            sizes_array = sizes_array[~np.isnan(sizes_array) & (sizes_array > 0)]
        else:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            logger.info(f"🔬 Size bins using single-solution Mie: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
            
            sampled_fsc = parsed_data[fsc_ch].values[sample_indices]
            
            # Use NORMALIZED batch conversion: FSC to size (handles scale mismatch)
            sizes_array, success_mask = mie_calc.diameters_from_scatter_normalized(
                sampled_fsc, min_diameter=10.0, max_diameter=500.0
            )
            sizes_array = sizes_array[success_mask & (sizes_array > 0)]
        
        # Bin sizes into categories
        small_count = np.sum(sizes_array < 50)
        medium_count = np.sum((sizes_array >= 50) & (sizes_array <= 200))
        large_count = np.sum(sizes_array > 200)
        
        total_binned = small_count + medium_count + large_count
        
        # Extrapolate to full dataset
        scale_factor = total_events / sample_size if total_binned > 0 else 1.0
        
        small_total = int(small_count * scale_factor)
        medium_total = int(medium_count * scale_factor)
        large_total = int(large_count * scale_factor)
        
        # Calculate percentages
        total_categorized = small_total + medium_total + large_total
        small_pct = (small_total / total_categorized * 100) if total_categorized > 0 else 0
        medium_pct = (medium_total / total_categorized * 100) if total_categorized > 0 else 0
        large_pct = (large_total / total_categorized * 100) if total_categorized > 0 else 0
        
        logger.success(
            f"✅ Size bins for {sample_id}: "
            f"Small={small_pct:.1f}%, Medium={medium_pct:.1f}%, Large={large_pct:.1f}%"
        )
        
        return {
            "sample_id": sample_id,
            "total_events": total_events,
            "bins": {
                "small": small_total,
                "medium": medium_total,
                "large": large_total
            },
            "percentages": {
                "small": round(small_pct, 2),
                "medium": round(medium_pct, 2),
                "large": round(large_pct, 2)
            },
            "thresholds": {
                "small_max": 50,
                "medium_min": 50,
                "medium_max": 200,
                "large_min": 200
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get size bins for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get size bins: {str(e)}"
        )


# ============================================================================
# Distribution Analysis Endpoint (VAL-008 + STAT-001)
# ============================================================================

@router.get("/{sample_id}/distribution-analysis", response_model=dict)
async def get_distribution_analysis(
    sample_id: str,
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override (e.g., 'Channel_3')"),
    wavelength_nm: float = Query(488.0, ge=200, le=800, description="Laser wavelength for Mie calculations"),
    n_particle: float = Query(1.40, ge=1.0, le=2.0, description="Particle refractive index"),
    n_medium: float = Query(1.33, ge=1.0, le=2.0, description="Medium refractive index"),
    include_overlays: bool = Query(True, description="Include distribution overlay curves for plotting"),
    db: AsyncSession = Depends(get_session)
):
    """
    Perform comprehensive distribution analysis on particle size data.
    
    This endpoint runs multiple normality tests, fits various probability
    distributions (Normal, Log-normal, Gamma, Weibull), and provides
    recommendations for biological interpretation.
    
    **Key Features:**
    - Normality testing: Shapiro-Wilk, D'Agostino-Pearson, K-S, Anderson-Darling
    - Distribution fitting: Normal, Log-normal (recommended), Gamma, Weibull
    - AIC/BIC model comparison for best statistical fit
    - Overlay curves for histogram visualization
    
    **Response:**
    ```json
    {
        "sample_id": "PC3_EXO1",
        "n_samples": 5000,
        "normality_tests": {
            "tests": {...},
            "is_normal": false,
            "conclusion": "Data is NOT normally distributed (0/4 tests passed)"
        },
        "distribution_fits": {
            "fits": {...},
            "best_fit_aic": "weibull_min",
            "recommendation": "lognorm",
            "recommendation_reason": "Log-normal recommended for biological interpretation..."
        },
        "summary_statistics": {
            "mean": 120.5,
            "median": 95.2,
            "d10": 45.0,
            "d50": 95.2,
            "d90": 210.0,
            "skewness": 1.2,
            "skew_interpretation": "right-skewed (positive)"
        },
        "conclusion": {
            "is_normal": false,
            "recommended_distribution": "lognorm",
            "use_median": true,
            "central_tendency": 95.2,
            "central_tendency_metric": "median (D50)"
        },
        "overlays": {...}
    }
    ```
    
    **Notes:**
    - EV size distributions are typically NOT normal (usually right-skewed)
    - Log-normal is biologically appropriate due to multiplicative growth processes
    - Use median (D50) instead of mean for non-normal distributions
    - Per MISEV2018 guidelines: report median with D10/D90 for EV sizing
    """
    from src.physics.statistics_utils import comprehensive_distribution_analysis
    from src.physics.mie_theory import MieCalculator
    from src.parser.fcs_parser import parse_fcs_to_dataframe
    
    try:
        # Get sample from database
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample has no FCS data for distribution analysis"
            )
        
        # Parse FCS file
        import os
        if not os.path.exists(sample.file_path_fcs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FCS file not found: {sample.file_path_fcs}"
            )
        
        parsed_data = parse_fcs_to_dataframe(sample.file_path_fcs)
        if parsed_data.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data in FCS file"
            )
        
        # Determine FSC channel
        available_channels = parsed_data.columns.tolist()
        
        if fsc_channel and fsc_channel in available_channels:
            selected_fsc = fsc_channel
        else:
            # Auto-detect FSC channel
            fsc_candidates = ['FSC-H', 'FSC-A', 'FSC_H', 'FSC_A', 'BFSC-H', 'BFSC-A']
            selected_fsc = None
            for candidate in fsc_candidates:
                if candidate in available_channels:
                    selected_fsc = candidate
                    break
            
            if not selected_fsc:
                # Try partial match
                for ch in available_channels:
                    if 'FSC' in ch.upper():
                        selected_fsc = ch
                        break
        
        if not selected_fsc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No FSC channel found. Available: {available_channels[:10]}"
            )
        
        # Get FSC values and convert to particle sizes
        import numpy as np
        fsc_values = parsed_data[selected_fsc].values
        fsc_values = fsc_values[np.isfinite(fsc_values) & (fsc_values > 0)]
        
        if len(fsc_values) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient valid FSC data (n={len(fsc_values)}, need ≥10)"
            )
        
        # Initialize Mie calculator and convert to sizes
        mie = MieCalculator(
            wavelength_nm=wavelength_nm,
            n_particle=n_particle,
            n_medium=n_medium
        )
        
        # Normalize FSC values for Mie conversion
        fsc_normalized = fsc_values / np.max(fsc_values)
        
        # Convert to particle sizes (vectorized operation)
        sizes_nm = np.array([
            mie.inverse_solve_size(fsc, max_size=1000)
            for fsc in fsc_normalized[:min(len(fsc_normalized), 10000)]
        ])
        
        # Filter valid sizes
        sizes_nm = sizes_nm[np.isfinite(sizes_nm) & (sizes_nm > 0) & (sizes_nm < 1000)]
        
        if len(sizes_nm) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient valid size data after Mie conversion (n={len(sizes_nm)})"
            )
        
        logger.info(f"📊 Running distribution analysis for {sample_id} with {len(sizes_nm)} particles")
        
        # Run comprehensive distribution analysis
        analysis = comprehensive_distribution_analysis(
            data=sizes_nm,
            include_overlays=include_overlays
        )
        
        # Add metadata to response
        analysis['sample_id'] = sample_id
        analysis['fsc_channel'] = selected_fsc
        analysis['mie_parameters'] = {
            'wavelength_nm': wavelength_nm,
            'n_particle': n_particle,
            'n_medium': n_medium
        }
        
        logger.info(
            f"✅ Distribution analysis complete for {sample_id}: "
            f"is_normal={analysis['conclusion']['is_normal']}, "
            f"recommended={analysis['conclusion']['recommended_distribution']}"
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to run distribution analysis for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Distribution analysis failed: {str(e)}"
        )


# ============================================================================
# Anomaly Detection Endpoint
# ============================================================================

@router.get("/{sample_id}/anomaly-detection", response_model=dict)
async def detect_anomalies(
    sample_id: str,
    method: str = Query("zscore", description="Anomaly method: zscore, iqr, both"),
    zscore_threshold: float = Query(3.0, ge=1.0, le=10.0, description="Z-score threshold"),
    iqr_factor: float = Query(1.5, ge=1.0, le=5.0, description="IQR factor for outlier detection"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name override"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name override"),
    db: AsyncSession = Depends(get_session)
):
    """
    Run anomaly detection on a sample's scatter data.
    
    Uses statistical methods (Z-score and/or IQR) to detect anomalous events.
    
    **Parameters:**
    - method: Detection method - "zscore", "iqr", or "both"
    - zscore_threshold: Z-score threshold (default 3.0)
    - iqr_factor: IQR factor for outlier detection (default 1.5)
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "enabled": true,
        "method": "zscore",
        "total_anomalies": 250,
        "anomaly_percentage": 2.5,
        "anomalous_indices": [123, 456, ...]
    }
    ```
    """
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.utils.channel_config import get_channel_config
        import numpy as np
        
        logger.info(f"🔍 Running anomaly detection for sample: {sample_id}")
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Get channels
        channels = parser.channel_names
        channel_config = get_channel_config()
        
        fsc_ch = fsc_channel or channel_config.detect_fsc_channel(channels)
        ssc_ch = ssc_channel or channel_config.detect_ssc_channel(channels)
        
        if not fsc_ch and len(channels) >= 1:
            fsc_ch = channels[0]
        if not ssc_ch and len(channels) >= 2:
            ssc_ch = channels[1]
        
        if not fsc_ch or not ssc_ch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find FSC/SSC channels. Available: {', '.join(channels)}"
            )
        
        # Run anomaly detection
        fsc_values = parsed_data[fsc_ch].values
        ssc_values = parsed_data[ssc_ch].values
        
        anomalous_indices = set()
        
        if method in ['zscore', 'both']:
            # Z-score based detection
            fsc_mean, fsc_std = np.mean(fsc_values), np.std(fsc_values)
            ssc_mean, ssc_std = np.mean(ssc_values), np.std(ssc_values)
            
            fsc_zscore = np.abs((fsc_values - fsc_mean) / (fsc_std + 1e-10))
            ssc_zscore = np.abs((ssc_values - ssc_mean) / (ssc_std + 1e-10))
            
            zscore_outliers = np.where((fsc_zscore > zscore_threshold) | (ssc_zscore > zscore_threshold))[0]
            anomalous_indices.update(zscore_outliers.tolist())
        
        if method in ['iqr', 'both']:
            # IQR based detection
            fsc_q1, fsc_q3 = np.percentile(fsc_values, [25, 75])
            ssc_q1, ssc_q3 = np.percentile(ssc_values, [25, 75])
            
            fsc_iqr = fsc_q3 - fsc_q1
            ssc_iqr = ssc_q3 - ssc_q1
            
            fsc_lower, fsc_upper = fsc_q1 - iqr_factor * fsc_iqr, fsc_q3 + iqr_factor * fsc_iqr
            ssc_lower, ssc_upper = ssc_q1 - iqr_factor * ssc_iqr, ssc_q3 + iqr_factor * ssc_iqr
            
            iqr_outliers = np.where(
                (fsc_values < fsc_lower) | (fsc_values > fsc_upper) |
                (ssc_values < ssc_lower) | (ssc_values > ssc_upper)
            )[0]
            anomalous_indices.update(iqr_outliers.tolist())
        
        anomalous_list = sorted(list(anomalous_indices))
        total_events = len(parsed_data)
        anomaly_percentage = (len(anomalous_list) / total_events * 100) if total_events > 0 else 0
        
        logger.success(
            f"✅ Anomaly detection for {sample_id}: "
            f"{len(anomalous_list)} anomalies ({anomaly_percentage:.2f}%)"
        )
        
        return {
            "sample_id": sample_id,
            "enabled": True,
            "method": method,
            "total_anomalies": len(anomalous_list),
            "anomaly_percentage": round(anomaly_percentage, 2),
            "anomalous_indices": anomalous_list,
            "settings": {
                "zscore_threshold": zscore_threshold,
                "iqr_factor": iqr_factor
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed anomaly detection for {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed anomaly detection: {str(e)}"
        )


# ============================================================================
# Re-analyze Sample Endpoint
# ============================================================================

from pydantic import BaseModel, Field


class ReanalyzeRequest(BaseModel):
    """Request body for re-analyzing a sample with custom settings."""
    wavelength_nm: float = Field(default=488.0, ge=200, le=800, description="Laser wavelength in nm")
    n_particle: float = Field(default=1.40, ge=1.0, le=2.0, description="Particle refractive index")
    n_medium: float = Field(default=1.33, ge=1.0, le=2.0, description="Medium refractive index")
    anomaly_detection: bool = Field(default=False, description="Enable anomaly detection")
    anomaly_method: str = Field(default="zscore", description="Anomaly method: zscore, iqr, both")
    zscore_threshold: float = Field(default=3.0, ge=1.0, le=10.0, description="Z-score threshold")
    iqr_factor: float = Field(default=1.5, ge=1.0, le=5.0, description="IQR factor for outlier detection")
    size_ranges: list[dict] = Field(
        default=[
            {"name": "Small EVs", "min": 30, "max": 100},
            {"name": "Medium EVs", "min": 100, "max": 200},
            {"name": "Large EVs", "min": 200, "max": 500},
        ],
        description="Custom size ranges for binning"
    )


@router.post("/{sample_id}/reanalyze", response_model=dict)
async def reanalyze_sample(
    sample_id: str,
    request: ReanalyzeRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Re-analyze a sample with custom analysis settings.
    
    This endpoint re-processes the FCS file with user-specified parameters
    and returns updated statistics without modifying the database.
    
    **Use Cases:**
    - Change laser wavelength for Mie calculations
    - Adjust refractive index parameters
    - Enable/disable anomaly detection
    - Apply custom size range binning
    """
    import numpy as np
    
    try:
        # Get sample
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        # Check if FCS file exists
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        logger.info(f"🔄 Re-analyzing sample {sample_id} with params: λ={request.wavelength_nm}nm, n_p={request.n_particle}, n_m={request.n_medium}")
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        import numpy as np
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        stats = parser.get_statistics()
        
        # Detect FSC and SSC channels
        channels = list(parsed_data.columns)
        fsc_channel = None
        ssc_channel = None
        
        for ch in channels:
            ch_upper = ch.upper()
            if 'FSC' in ch_upper:
                if '-H' in ch_upper or '_H' in ch_upper:
                    fsc_channel = ch
                elif '-A' in ch_upper or '_A' in ch_upper and fsc_channel is None:
                    fsc_channel = ch
                elif fsc_channel is None:
                    fsc_channel = ch
            elif 'SSC' in ch_upper:
                if '-H' in ch_upper or '_H' in ch_upper:
                    ssc_channel = ch
                elif '-A' in ch_upper or '_A' in ch_upper and ssc_channel is None:
                    ssc_channel = ch
                elif ssc_channel is None:
                    ssc_channel = ch
        
        # Get statistics for detected channels
        fsc_stats = stats.get(fsc_channel, {}) if fsc_channel else {}
        ssc_stats = stats.get(ssc_channel, {}) if ssc_channel else {}
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in parsed_data.columns and
            multi_solution_info['bssc_channel'] in parsed_data.columns
        )
        
        # Calculate particle size and size distribution
        particle_size_median_nm = None
        size_distribution = None
        custom_bins = {}
        
        if can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 Re-analyze using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            multi_mie_calc = MultiSolutionMieCalculator(
                n_particle=request.n_particle, 
                n_medium=request.n_medium
            )
            
            # Sample for performance
            sample_size = min(10000, len(parsed_data))
            np.random.seed(42)
            sample_indices = np.random.choice(len(parsed_data), size=sample_size, replace=False)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(parsed_data[vssc_ch].values[sample_indices], dtype=np.float64)
            ssc_blue = np.asarray(parsed_data[bssc_ch].values[sample_indices], dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes_array, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            valid_sizes = sizes_array[~np.isnan(sizes_array) & (sizes_array > 0)]
            
            if len(valid_sizes) > 0:
                particle_size_median_nm = float(np.median(valid_sizes))
                size_distribution = {
                    'd10': float(np.percentile(valid_sizes, 10)),
                    'd50': float(np.percentile(valid_sizes, 50)),
                    'd90': float(np.percentile(valid_sizes, 90)),
                    'mean': float(np.mean(valid_sizes)),
                    'std': float(np.std(valid_sizes))
                }
                
                # Calculate custom size range bins
                scale_factor = len(parsed_data) / sample_size
                for range_def in request.size_ranges:
                    name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                    min_size = range_def.get('min', 0)
                    max_size = range_def.get('max', 1000)
                    count = np.sum((valid_sizes >= min_size) & (valid_sizes < max_size))
                    custom_bins[name] = {
                        'count': int(count * scale_factor),
                        'percentage': float(count / len(valid_sizes) * 100) if len(valid_sizes) > 0 else 0
                    }
        else:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=request.wavelength_nm,
                n_particle=request.n_particle,
                n_medium=request.n_medium
            )
            logger.info(f"🔬 Re-analyze using single-solution Mie: λ={request.wavelength_nm}nm")
            
            # Calculate particle size from FSC median
            if fsc_stats.get('median'):
                try:
                    diameter, success = mie_calc.diameter_from_scatter(
                        fsc_intensity=fsc_stats['median'],
                        min_diameter=10.0,
                        max_diameter=500.0
                    )
                    if success:
                        particle_size_median_nm = float(diameter)
                except Exception as mie_error:
                    logger.warning(f"⚠️ Mie calculation failed: {mie_error}")
            
            # Calculate size distribution
            if fsc_channel and fsc_channel in parsed_data.columns:
                try:
                    # Sample for performance
                    sample_size = min(10000, len(parsed_data))
                    sampled_fsc = parsed_data[fsc_channel].sample(n=sample_size, random_state=42)
                    
                    sizes = []
                    for fsc_val in sampled_fsc:
                        size, success = mie_calc.diameter_from_scatter(
                            fsc_intensity=float(fsc_val),
                            min_diameter=10.0,
                            max_diameter=500.0
                        )
                        if success and size > 0:
                            sizes.append(size)
                    
                    if sizes:
                        sizes_array = np.array(sizes)
                        size_distribution = {
                            'd10': float(np.percentile(sizes_array, 10)),
                            'd50': float(np.percentile(sizes_array, 50)),
                            'd90': float(np.percentile(sizes_array, 90)),
                            'mean': float(np.mean(sizes_array)),
                            'std': float(np.std(sizes_array))
                        }
                        
                        # Calculate custom size range bins
                        scale_factor = len(parsed_data) / sample_size
                        for range_def in request.size_ranges:
                            name = range_def.get('name', f"{range_def['min']}-{range_def['max']}nm")
                            min_size = range_def.get('min', 0)
                            max_size = range_def.get('max', 1000)
                            count = np.sum((sizes_array >= min_size) & (sizes_array < max_size))
                            custom_bins[name] = {
                                'count': int(count * scale_factor),
                                'percentage': float(count / len(sizes_array) * 100) if sizes_array.size > 0 else 0
                            }
                            
                except Exception as size_error:
                    logger.warning(f"⚠️ Size distribution calculation failed: {size_error}")
        
        # Anomaly detection
        anomaly_data = None
        if request.anomaly_detection:
            try:
                anomalous_indices = []
                
                if fsc_channel and ssc_channel:
                    fsc_data = parsed_data[fsc_channel].values
                    ssc_data = parsed_data[ssc_channel].values
                    
                    if request.anomaly_method in ['zscore', 'both']:
                        # Z-score method
                        fsc_zscore = np.abs((fsc_data - np.mean(fsc_data)) / np.std(fsc_data))
                        ssc_zscore = np.abs((ssc_data - np.mean(ssc_data)) / np.std(ssc_data))
                        zscore_outliers = np.where((fsc_zscore > request.zscore_threshold) | (ssc_zscore > request.zscore_threshold))[0]
                        anomalous_indices.extend(zscore_outliers.tolist())
                    
                    if request.anomaly_method in ['iqr', 'both']:
                        # IQR method
                        fsc_q1, fsc_q3 = np.percentile(fsc_data, [25, 75])
                        ssc_q1, ssc_q3 = np.percentile(ssc_data, [25, 75])
                        fsc_iqr = fsc_q3 - fsc_q1
                        ssc_iqr = ssc_q3 - ssc_q1
                        fsc_outliers = (fsc_data < fsc_q1 - request.iqr_factor * fsc_iqr) | (fsc_data > fsc_q3 + request.iqr_factor * fsc_iqr)
                        ssc_outliers = (ssc_data < ssc_q1 - request.iqr_factor * ssc_iqr) | (ssc_data > ssc_q3 + request.iqr_factor * ssc_iqr)
                        iqr_outliers = np.where(fsc_outliers | ssc_outliers)[0]
                        anomalous_indices.extend(iqr_outliers.tolist())
                    
                    anomalous_indices = list(set(anomalous_indices))
                    
                    anomaly_data = {
                        'enabled': True,
                        'method': request.anomaly_method,
                        'total_anomalies': len(anomalous_indices),
                        'anomaly_percentage': len(anomalous_indices) / len(parsed_data) * 100,
                        'anomalous_indices': anomalous_indices[:1000]  # Limit for response size
                    }
            except Exception as anomaly_error:
                logger.warning(f"⚠️ Anomaly detection failed: {anomaly_error}")
        
        # Build response
        response = {
            'sample_id': sample_id,
            'analysis_settings': {
                'wavelength_nm': request.wavelength_nm,
                'n_particle': request.n_particle,
                'n_medium': request.n_medium,
                'anomaly_detection': request.anomaly_detection,
                'anomaly_method': request.anomaly_method if request.anomaly_detection else None,
            },
            'results': {
                'total_events': len(parsed_data),
                'channels': channels[:10],  # First 10 channels
                'fsc_channel': fsc_channel,
                'ssc_channel': ssc_channel,
                'fsc_mean': fsc_stats.get('mean'),
                'fsc_median': fsc_stats.get('median'),
                'ssc_mean': ssc_stats.get('mean'),
                'ssc_median': ssc_stats.get('median'),
                'particle_size_median_nm': particle_size_median_nm,
                'size_statistics': size_distribution,
                'custom_size_bins': custom_bins,
            },
            'anomaly_data': anomaly_data,
        }
        
        logger.success(f"✅ Re-analyzed {sample_id}: {len(parsed_data)} events, median size={particle_size_median_nm}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to re-analyze {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-analyze sample: {str(e)}"
        )


# ============================================================================
# Experimental Conditions Endpoints (TASK-009)
# ============================================================================

from pydantic import BaseModel
from src.database.crud import (
    create_experimental_conditions,
    get_experimental_conditions_by_sample,
    update_experimental_conditions as update_conditions_db,
)


class ExperimentalConditionsCreate(BaseModel):
    """Request model for creating experimental conditions."""
    operator: str
    temperature_celsius: Optional[float] = None
    ph: Optional[float] = None
    substrate_buffer: Optional[str] = None
    custom_buffer: Optional[str] = None
    sample_volume_ul: Optional[float] = None
    dilution_factor: Optional[int] = None
    antibody_used: Optional[str] = None
    antibody_concentration_ug: Optional[float] = None
    incubation_time_min: Optional[float] = None
    sample_type: Optional[str] = None
    filter_size_um: Optional[float] = None
    notes: Optional[str] = None


class ExperimentalConditionsUpdate(BaseModel):
    """Request model for updating experimental conditions."""
    operator: Optional[str] = None
    temperature_celsius: Optional[float] = None
    ph: Optional[float] = None
    substrate_buffer: Optional[str] = None
    custom_buffer: Optional[str] = None
    sample_volume_ul: Optional[float] = None
    dilution_factor: Optional[int] = None
    antibody_used: Optional[str] = None
    antibody_concentration_ug: Optional[float] = None
    incubation_time_min: Optional[float] = None
    sample_type: Optional[str] = None
    filter_size_um: Optional[float] = None
    notes: Optional[str] = None


@router.post("/{sample_id}/conditions", response_model=dict)
async def save_experimental_conditions(
    sample_id: str,
    conditions: ExperimentalConditionsCreate,
    db: AsyncSession = Depends(get_session)
):
    """
    Save experimental conditions for a sample.
    
    TASK-009: Store experimental metadata for reproducibility and AI analysis.
    
    **Request Body:**
    ```json
    {
        "operator": "John Doe",
        "temperature_celsius": 22.5,
        "substrate_buffer": "PBS",
        "antibody_used": "CD81",
        "antibody_concentration_ug": 1.0,
        "incubation_time_min": 30,
        "notes": "Standard protocol"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "conditions_id": 1,
        "sample_id": "P5_F10_CD81",
        "message": "Experimental conditions saved successfully"
    }
    ```
    """
    logger.info(f"📝 Saving experimental conditions for sample: {sample_id}")
    
    try:
        # Find sample by sample_id string
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Create experimental conditions
        conditions_record = await create_experimental_conditions(
            db=db,
            sample_id=sample.id,  # type: ignore[arg-type]
            operator=conditions.operator,
            temperature_celsius=conditions.temperature_celsius,
            ph=conditions.ph,
            substrate_buffer=conditions.substrate_buffer,
            custom_buffer=conditions.custom_buffer,
            sample_volume_ul=conditions.sample_volume_ul,
            dilution_factor=conditions.dilution_factor,
            antibody_used=conditions.antibody_used,
            antibody_concentration_ug=conditions.antibody_concentration_ug,
            incubation_time_min=conditions.incubation_time_min,
            sample_type=conditions.sample_type,
            filter_size_um=conditions.filter_size_um,
            notes=conditions.notes,
        )
        
        logger.success(f"✅ Saved experimental conditions for sample {sample_id}")
        
        return {
            "success": True,
            "conditions_id": conditions_record.id,
            "sample_id": sample_id,
            "conditions": conditions_record.to_dict(),
            "message": "Experimental conditions saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to save conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save experimental conditions: {str(e)}"
        )


@router.get("/{sample_id}/conditions", response_model=dict)
async def get_experimental_conditions(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get experimental conditions for a sample.
    
    **Response:**
    ```json
    {
        "sample_id": "P5_F10_CD81",
        "conditions": {
            "id": 1,
            "operator": "John Doe",
            "temperature_celsius": 22.5,
            ...
        }
    }
    ```
    """
    try:
        # Find sample by sample_id string
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get conditions
        conditions = await get_experimental_conditions_by_sample(db, sample.id)  # type: ignore[arg-type]
        
        return {
            "sample_id": sample_id,
            "has_conditions": conditions is not None,
            "conditions": conditions.to_dict() if conditions else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experimental conditions: {str(e)}"
        )


@router.put("/{sample_id}/conditions", response_model=dict)
async def update_experimental_conditions(
    sample_id: str,
    conditions: ExperimentalConditionsUpdate,
    db: AsyncSession = Depends(get_session)
):
    """
    Update experimental conditions for a sample.
    """
    logger.info(f"📝 Updating experimental conditions for sample: {sample_id}")
    
    try:
        # Find sample
        query = select(Sample).where(Sample.sample_id == sample_id)
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        # Get existing conditions
        existing = await get_experimental_conditions_by_sample(db, sample.id)  # type: ignore[arg-type]
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No experimental conditions found for sample: {sample_id}"
            )
        
        # Build update dict (only non-None values)
        update_data = conditions.model_dump(exclude_unset=True)
        
        # Update conditions
        updated = await update_conditions_db(db, existing.id, **update_data)  # type: ignore[arg-type]
        
        return {
            "success": True,
            "sample_id": sample_id,
            "conditions": updated.to_dict() if updated else None,
            "message": "Experimental conditions updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to update conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experimental conditions: {str(e)}"
        )


# ============================================================================
# Channel Configuration Endpoints
# ============================================================================

@router.get("/channel-config", response_model=dict)
async def get_channel_configuration():
    """
    Get current channel configuration for FCS analysis.
    
    Returns the active instrument settings and all available instrument configurations.
    """
    try:
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        
        config = get_channel_config()
        
        return {
            "success": True,
            "active_instrument": config.active_instrument,
            "instruments": list(config.list_instruments()),
            "fsc_channels": config.get_fsc_channel_names(),
            "ssc_channels": config.get_ssc_channel_names(),
            "preferred": {
                "for_size_analysis": config.get_preferred_channels("for_size_analysis"),
                "for_scatter_plot": config.get_preferred_channels("for_scatter_plot")
            }
        }
    except Exception as e:
        logger.exception(f"❌ Failed to get channel config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel configuration: {str(e)}"
        )


@router.put("/channel-config", response_model=dict)
async def update_channel_configuration(
    instrument: Optional[str] = Query(None, description="Instrument name to activate"),
    fsc_channel: Optional[str] = Query(None, description="FSC channel name to add/set as preferred"),
    ssc_channel: Optional[str] = Query(None, description="SSC channel name to add/set as preferred"),
    save: bool = Query(True, description="Save configuration to file")
):
    """
    Update channel configuration for FCS analysis.
    
    **Parameters:**
    - instrument: Activate a specific instrument configuration
    - fsc_channel: Set the preferred FSC channel
    - ssc_channel: Set the preferred SSC channel
    - save: Whether to persist changes to file (default: True)
    
    **Example:**
    ```
    PUT /samples/channel-config?fsc_channel=Channel_5&ssc_channel=Channel_6&save=true
    ```
    """
    try:
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        
        config = get_channel_config()
        
        # Activate specific instrument if provided
        if instrument:
            if not config.set_active_instrument(instrument):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Instrument '{instrument}' not found. Available: {config.list_instruments()}"
                )
        
        # Add custom channel mapping if both FSC and SSC provided
        if fsc_channel and ssc_channel:
            config.add_custom_channel_mapping(fsc_channel, ssc_channel)
            logger.info(f"✓ Updated channel mapping: FSC={fsc_channel}, SSC={ssc_channel}")
        
        # Save configuration if requested
        if save:
            config.save_config()
        
        return {
            "success": True,
            "message": "Channel configuration updated",
            "active_instrument": config.active_instrument,
            "preferred_fsc": config.get_preferred_channels()[0],
            "preferred_ssc": config.get_preferred_channels()[1],
            "saved": save
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to update channel config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update channel configuration: {str(e)}"
        )


@router.get("/{sample_id}/available-channels", response_model=dict)
async def get_available_channels(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get available channels for a specific FCS sample.
    
    Returns all channel names from the FCS file with statistics to help identify
    FSC/SSC channels.
    """
    try:
        # Get sample
        result = await db.execute(
            select(Sample).where(Sample.sample_id == sample_id)
        )
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample not found: {sample_id}"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        from src.parsers.fcs_parser import FCSParser  # type: ignore[import-not-found]
        from src.utils.channel_config import get_channel_config  # type: ignore[import-not-found]
        import numpy as np
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        config = get_channel_config()
        
        # Build channel info with statistics
        channels_info = []
        for i, col in enumerate(parsed_data.columns):
            if col in ['sample_id', 'biological_sample_id', 'measurement_id', 
                       'is_baseline', 'file_name', 'instrument_type', 'parse_timestamp']:
                continue
            
            mean_val = parsed_data[col].mean()
            max_val = parsed_data[col].max()
            min_val = parsed_data[col].min()
            std_val = parsed_data[col].std()
            
            # Check if this is a detected FSC/SSC channel
            is_fsc = col in config.get_fsc_channel_names()
            is_ssc = col in config.get_ssc_channel_names()
            
            channels_info.append({
                "index": i + 1,
                "name": col,
                "mean": float(mean_val),
                "max": float(max_val),
                "min": float(min_val),
                "std": float(std_val),
                "cv": float(std_val / mean_val * 100) if mean_val > 0 else 0,
                "is_configured_fsc": is_fsc,
                "is_configured_ssc": is_ssc
            })
        
        # Detect channels based on config
        detected_fsc = config.detect_fsc_channel(parser.channel_names)
        detected_ssc = config.detect_ssc_channel(parser.channel_names)
        
        return {
            "sample_id": sample_id,
            "file_name": sample.file_path_fcs.name if sample.file_path_fcs else None,
            "total_events": len(parsed_data),
            "channels": channels_info,
            "detected_fsc": detected_fsc,
            "detected_ssc": detected_ssc,
            "active_instrument": config.active_instrument,
            "recommendation": (
                f"For accurate EV sizing, configure FSC={detected_fsc or 'Channel_5'} "
                f"and SSC={detected_ssc or 'Channel_6'}"
            ) if not detected_fsc or not detected_ssc else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get available channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available channels: {str(e)}"
        )


# ============================================================================
# FCS Data Split - Metadata and Values (Per-Event Sizes)
# ============================================================================

@router.get("/{sample_id}/fcs/metadata", response_model=dict)
async def get_fcs_metadata(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS file metadata only (no event data).
    
    Returns instrument settings, channel info, acquisition details.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        parser = FCSParser(sample.file_path_fcs)
        parser.parse()
        
        # Extract metadata
        metadata = parser.extract_metadata()
        
        # Add file-level info
        import os
        file_stat = os.stat(sample.file_path_fcs)
        
        return {
            "sample_id": sample_id,
            "file_info": {
                "file_name": sample.file_path_fcs.name if hasattr(sample.file_path_fcs, 'name') else str(sample.file_path_fcs).split('/')[-1],
                "file_size_bytes": file_stat.st_size,
                "file_size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            },
            "acquisition": {
                "date": metadata.get('acquisition_date', 'Unknown'),
                "time": metadata.get('acquisition_time', 'Unknown'),
                "cytometer": metadata.get('cytometer', 'Unknown'),
                "operator": metadata.get('operator', 'Unknown'),
                "specimen": metadata.get('specimen', 'Unknown'),
            },
            "data_info": {
                "total_events": metadata.get('total_events', 0),
                "parameter_count": metadata.get('parameters', 0),
                "channel_count": metadata.get('channel_count', 0),
                "channel_names": metadata.get('channel_names', []),
            },
            "channels": metadata.get('channels', {}),
            "identifiers": {
                "sample_id": metadata.get('sample_id'),
                "biological_sample_id": metadata.get('biological_sample_id'),
                "measurement_id": metadata.get('measurement_id'),
                "is_baseline": metadata.get('is_baseline', False),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS metadata: {str(e)}"
        )


@router.get("/{sample_id}/fcs/values", response_model=dict)
async def get_fcs_values(
    sample_id: str,
    wavelength_nm: float = Query(488.0, description="Laser wavelength in nm"),
    n_particle: float = Query(1.40, description="Particle refractive index"),
    n_medium: float = Query(1.33, description="Medium refractive index"),
    max_events: int = Query(50000, ge=1, le=500000, description="Maximum events to return"),
    include_raw_channels: bool = Query(False, description="Include raw FSC/SSC channel values"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get FCS per-event size values calculated using Mie theory.
    
    Returns particle diameter (nm) for each event calculated from FSC using Mie scattering.
    
    **Parameters:**
    - wavelength_nm: Laser wavelength (default: 488nm)
    - n_particle: Particle refractive index (default: 1.40 for EVs)
    - n_medium: Medium refractive index (default: 1.33 for PBS)
    - max_events: Maximum number of events to return (default: 50000)
    - include_raw_channels: If true, include raw FSC/SSC values
    
    **Response:**
    Returns per-event size data and summary statistics.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_fcs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No FCS file associated with sample {sample_id}"
            )
        
        logger.info(f"📊 Getting FCS values for {sample_id} with Mie params: λ={wavelength_nm}nm, n_p={n_particle}, n_m={n_medium}")
        
        # Parse FCS file
        from src.parsers.fcs_parser import FCSParser
        from src.utils.channel_config import ChannelConfig
        import numpy as np
        
        parser = FCSParser(sample.file_path_fcs)
        parsed_data = parser.parse()
        
        # Detect FSC channel
        config = ChannelConfig()
        channels = parser.channel_names
        fsc_channel = config.detect_fsc_channel(channels)
        ssc_channel = config.detect_ssc_channel(channels)
        
        if not fsc_channel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No FSC channel detected - cannot calculate particle sizes"
            )
        
        # Sample events if needed
        total_events = len(parsed_data)
        if total_events > max_events:
            np.random.seed(42)
            sample_indices = np.random.choice(total_events, size=max_events, replace=False)
            sampled_data = parsed_data.iloc[sample_indices].reset_index(drop=True)
            sampled = True
        else:
            sampled_data = parsed_data
            sample_indices = np.arange(total_events)
            sampled = False
        
        # Check for multi-solution Mie capability
        multi_solution_info = detect_multi_solution_channels(channels)
        can_use_multi_solution = (
            multi_solution_info['can_use_multi_solution'] and
            multi_solution_info['vssc_channel'] in sampled_data.columns and
            multi_solution_info['bssc_channel'] in sampled_data.columns
        )
        
        # Get FSC values
        fsc_values = sampled_data[fsc_channel].values
        
        if can_use_multi_solution:
            # === MULTI-SOLUTION MIE (PREFERRED) ===
            from src.physics.mie_scatter import MultiSolutionMieCalculator
            
            vssc_ch = multi_solution_info['vssc_channel']
            bssc_ch = multi_solution_info['bssc_channel']
            
            logger.info(f"🔬 FCS values using MULTI-SOLUTION Mie: VSSC={vssc_ch}, BSSC={bssc_ch}")
            
            multi_mie_calc = MultiSolutionMieCalculator(n_particle=n_particle, n_medium=n_medium)
            
            # Get SSC values for both wavelengths
            ssc_violet = np.asarray(sampled_data[vssc_ch].values, dtype=np.float64)
            ssc_blue = np.asarray(sampled_data[bssc_ch].values, dtype=np.float64)
            
            # Calculate sizes with disambiguation
            sizes, num_solutions = multi_mie_calc.calculate_sizes_multi_solution(ssc_blue, ssc_violet)
            success_mask = ~np.isnan(sizes) & (sizes > 0)
        else:
            # === SINGLE-SOLUTION MIE (FALLBACK) ===
            from src.physics.mie_scatter import MieScatterCalculator
            mie_calc = MieScatterCalculator(
                wavelength_nm=wavelength_nm,
                n_particle=n_particle,
                n_medium=n_medium
            )
            logger.info(f"🔬 FCS values using single-solution Mie: λ={wavelength_nm}nm")
            
            # Calculate particle sizes using NORMALIZED method
            # This handles the scale mismatch between raw FSC and physical scatter
            sizes, success_mask = mie_calc.diameters_from_scatter_normalized(
                fsc_values, 
                min_diameter=20.0, 
                max_diameter=500.0
            )
        
        # Filter valid sizes
        valid_sizes = sizes[success_mask]
        valid_fsc = fsc_values[success_mask]
        
        # Build response
        event_data = []
        for i, (size, fsc) in enumerate(zip(sizes, fsc_values)):
            event_entry = {
                "event_id": i,
                "diameter_nm": float(size) if success_mask[i] else None,
                "valid": bool(success_mask[i]),
            }
            if include_raw_channels:
                event_entry["fsc"] = float(fsc)
                if ssc_channel:
                    event_entry["ssc"] = float(sampled_data.iloc[i][ssc_channel])
            event_data.append(event_entry)
        
        # Calculate statistics
        if len(valid_sizes) > 0:
            size_stats = {
                "count": int(len(valid_sizes)),
                "mean_nm": float(np.mean(valid_sizes)),
                "median_nm": float(np.median(valid_sizes)),
                "std_nm": float(np.std(valid_sizes)),
                "min_nm": float(np.min(valid_sizes)),
                "max_nm": float(np.max(valid_sizes)),
                "d10_nm": float(np.percentile(valid_sizes, 10)),
                "d50_nm": float(np.percentile(valid_sizes, 50)),
                "d90_nm": float(np.percentile(valid_sizes, 90)),
            }
            
            # Size distribution bins
            bins = [0, 50, 100, 150, 200, 300, 500, 1000]
            bin_labels = ["<50", "50-100", "100-150", "150-200", "200-300", "300-500", ">500"]
            hist, _ = np.histogram(valid_sizes, bins=bins)
            size_distribution = {label: int(count) for label, count in zip(bin_labels, hist)}
        else:
            size_stats = None
            size_distribution = None
        
        return {
            "sample_id": sample_id,
            "mie_parameters": {
                "wavelength_nm": wavelength_nm,
                "n_particle": n_particle,
                "n_medium": n_medium,
            },
            "data_info": {
                "total_events": total_events,
                "returned_events": len(sampled_data),
                "valid_sizes": int(np.sum(success_mask)),
                "invalid_sizes": int(np.sum(~success_mask)),
                "sampled": sampled,
                "fsc_channel": fsc_channel,
                "ssc_channel": ssc_channel,
            },
            "statistics": size_stats,
            "size_distribution": size_distribution,
            "events": event_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get FCS values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FCS values: {str(e)}"
        )


# ============================================================================
# NTA Data Split - Metadata and Values (Size/Concentration)
# ============================================================================

@router.get("/{sample_id}/nta/metadata", response_model=dict)
async def get_nta_metadata(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA file metadata only (no measurement data).
    
    Returns instrument settings, acquisition parameters, sample info.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_nta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No NTA file associated with sample {sample_id}"
            )
        
        # Parse NTA file
        from src.parsers.nta_parser import NTAParser
        parser = NTAParser(sample.file_path_nta)
        parser.parse()
        
        # Get raw metadata
        raw_metadata = parser.raw_metadata
        
        # Add file-level info
        import os
        file_stat = os.stat(sample.file_path_nta)
        
        return {
            "sample_id": sample_id,
            "file_info": {
                "file_name": sample.file_path_nta.name if hasattr(sample.file_path_nta, 'name') else str(sample.file_path_nta).split('/')[-1],
                "file_size_bytes": file_stat.st_size,
                "measurement_type": parser.measurement_type,
            },
            "sample_info": {
                "sample_name": raw_metadata.get('sample_name', 'Unknown'),
                "operator": raw_metadata.get('operator', 'Unknown'),
                "experiment": raw_metadata.get('experiment', 'Unknown'),
                "electrolyte": raw_metadata.get('electrolyte', 'Unknown'),
            },
            "instrument": {
                "instrument_serial": raw_metadata.get('instrument_serial', 'Unknown'),
                "cell_serial": raw_metadata.get('cell_serial', 'Unknown'),
                "software_version": raw_metadata.get('software_version', 'Unknown'),
                "sop": raw_metadata.get('sop', 'Unknown'),
            },
            "acquisition": {
                "date": raw_metadata.get('date', 'Unknown'),
                "time": raw_metadata.get('time', 'Unknown'),
                "temperature": float(raw_metadata.get('temperature', 0)) if raw_metadata.get('temperature') else None,
                "viscosity": float(raw_metadata.get('viscosity', 0)) if raw_metadata.get('viscosity') else None,
                "ph": float(raw_metadata.get('ph', 0)) if raw_metadata.get('ph') else None,
                "conductivity": float(raw_metadata.get('conductivity', 0)) if raw_metadata.get('conductivity') else None,
            },
            "measurement_params": {
                "num_positions": int(raw_metadata.get('num_positions', 0)) if raw_metadata.get('num_positions') else None,
                "num_traces": int(raw_metadata.get('num_traces', 0)) if raw_metadata.get('num_traces') else None,
                "sensitivity": float(raw_metadata.get('sensitivity', 0)) if raw_metadata.get('sensitivity') else None,
                "shutter": float(raw_metadata.get('shutter', 0)) if raw_metadata.get('shutter') else None,
                "laser_wavelength": float(raw_metadata.get('laser_wavelength', 0)) if raw_metadata.get('laser_wavelength') else None,
                "dilution": float(raw_metadata.get('dilution', 1)) if raw_metadata.get('dilution') else 1,
                "conc_correction": float(raw_metadata.get('conc_correction', 1)) if raw_metadata.get('conc_correction') else 1,
            },
            "quality": {
                "cell_check_result": raw_metadata.get('cell_check_result', 'Unknown'),
                "detected_particles": int(raw_metadata.get('detected_particles', 0)) if raw_metadata.get('detected_particles') else None,
                "scattering_intensity": float(raw_metadata.get('scattering_intensity', 0)) if raw_metadata.get('scattering_intensity') else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA metadata: {str(e)}"
        )


@router.get("/{sample_id}/nta/values", response_model=dict)
async def get_nta_values(
    sample_id: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get NTA size and concentration values.
    
    Returns size distribution data with size (nm) and concentration (particles/mL).
    
    **Response:**
    Returns per-bin size and concentration data along with summary statistics.
    """
    try:
        # Get sample from database
        result = await db.execute(select(Sample).where(Sample.sample_id == sample_id))
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample {sample_id} not found"
            )
        
        if not sample.file_path_nta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No NTA file associated with sample {sample_id}"
            )
        
        logger.info(f"📊 Getting NTA values for {sample_id}")
        
        # Parse NTA file
        from src.parsers.nta_parser import NTAParser
        import numpy as np
        
        parser = NTAParser(sample.file_path_nta)
        parsed_data = parser.parse()
        
        # Extract size and concentration columns
        size_col = None
        conc_col = None
        
        # Find size column
        for col in ['size_nm', 'Size (nm)', 'Diameter', 'diameter_nm']:
            if col in parsed_data.columns:
                size_col = col
                break
        
        # Find concentration column
        for col in ['concentration_particles_ml', 'Concentration (particles/mL)', 'concentration_particles_cm3', 'Conc.']:
            if col in parsed_data.columns:
                conc_col = col
                break
        
        if not size_col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No size column found in NTA data"
            )
        
        # Get values
        sizes = parsed_data[size_col].values
        concentrations = parsed_data[conc_col].values if conc_col else None
        
        # Build per-bin data
        values_data = []
        for i in range(len(sizes)):
            entry = {
                "bin_id": i,
                "size_nm": float(sizes[i]),
            }
            if concentrations is not None:
                entry["concentration_particles_ml"] = float(concentrations[i])
            values_data.append(entry)
        
        # Calculate statistics
        valid_sizes = sizes[~np.isnan(sizes)]
        if conc_col:
            valid_conc = concentrations[~np.isnan(concentrations)]
            # Weight sizes by concentration for proper mean
            total_particles = np.sum(valid_conc)
            if total_particles > 0:
                weighted_mean = np.sum(valid_sizes * valid_conc) / total_particles
            else:
                weighted_mean = np.mean(valid_sizes)
        else:
            valid_conc = None
            weighted_mean = np.mean(valid_sizes)
        
        size_stats = {
            "count": int(len(valid_sizes)),
            "mean_nm": float(np.mean(valid_sizes)),
            "weighted_mean_nm": float(weighted_mean),
            "median_nm": float(np.median(valid_sizes)),
            "std_nm": float(np.std(valid_sizes)),
            "min_nm": float(np.min(valid_sizes)),
            "max_nm": float(np.max(valid_sizes)),
            "mode_nm": float(valid_sizes[np.argmax(valid_conc)]) if valid_conc is not None and len(valid_conc) > 0 else float(np.median(valid_sizes)),
        }
        
        conc_stats = None
        if valid_conc is not None:
            conc_stats = {
                "total_particles_ml": float(np.sum(valid_conc)),
                "max_concentration": float(np.max(valid_conc)),
                "peak_size_nm": float(valid_sizes[np.argmax(valid_conc)]),
            }
        
        return {
            "sample_id": sample_id,
            "measurement_type": parser.measurement_type,
            "data_info": {
                "total_bins": len(parsed_data),
                "size_column": size_col,
                "concentration_column": conc_col,
            },
            "size_statistics": size_stats,
            "concentration_statistics": conc_stats,
            "values": values_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get NTA values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NTA values: {str(e)}"
        )

