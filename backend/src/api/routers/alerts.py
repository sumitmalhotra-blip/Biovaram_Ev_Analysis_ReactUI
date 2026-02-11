"""
Alerts Router (CRMIT-003)
=========================

API endpoints for alert management system.

Endpoints:
- GET    /alerts/          - List alerts with filtering
- GET    /alerts/counts    - Get alert counts by severity
- GET    /alerts/{id}      - Get single alert
- POST   /alerts/{id}/acknowledge - Acknowledge an alert
- POST   /alerts/acknowledge-multiple - Acknowledge multiple alerts
- DELETE /alerts/{id}      - Delete an alert

Author: CRMIT Backend Team
Date: December 31, 2025
Task: CRMIT-003 - Alert System with Timestamps
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.connection import get_session
from src.database.crud import (
    create_alert,
    get_alert_by_id,
    get_alerts,
    get_alert_counts,
    acknowledge_alert,
    acknowledge_multiple_alerts,
    delete_alert,
)
from src.database.models import AlertSeverity, AlertType
from src.api.auth_middleware import optional_auth


router = APIRouter()


# ============================================================================
# List Alerts
# ============================================================================

@router.get("/", response_model=dict)
async def list_alerts(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    sample_id: Optional[int] = Query(None, description="Filter by sample ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical, error)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    source: Optional[str] = Query(None, description="Filter by source (fcs_analysis, nta_analysis, etc.)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    db: AsyncSession = Depends(get_session)
):
    """
    List alerts with filtering and pagination.
    
    **Filter Options:**
    - `user_id`: Show only alerts for a specific user
    - `sample_id`: Show only alerts for a specific sample
    - `severity`: Filter by severity (info, warning, critical, error)
    - `alert_type`: Filter by type (anomaly_detected, quality_warning, etc.)
    - `is_acknowledged`: Filter by acknowledgment status
    - `source`: Filter by source (fcs_analysis, nta_analysis, qc_check)
    
    **Response:**
    ```json
    {
        "alerts": [
            {
                "id": 1,
                "alert_type": "anomaly_detected",
                "severity": "warning",
                "title": "High anomaly count detected",
                "message": "Sample P5_F10_CD81 has 150 anomalous events (15.0%)",
                "source": "fcs_analysis",
                "sample_name": "P5_F10_CD81",
                "is_acknowledged": false,
                "created_at": "2025-12-31T10:30:00Z"
            }
        ],
        "total": 25,
        "limit": 50,
        "offset": 0
    }
    ```
    """
    try:
        # Validate severity if provided
        if severity and severity not in ["info", "warning", "critical", "error"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}. Must be one of: info, warning, critical, error"
            )
        
        alerts = await get_alerts(
            db,
            user_id=user_id,
            sample_id=sample_id,
            severity=severity,
            alert_type=alert_type,
            is_acknowledged=is_acknowledged,
            source=source,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )
        
        return {
            "alerts": [alert.to_dict() for alert in alerts],
            "total": len(alerts),
            "limit": limit,
            "offset": offset,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to list alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list alerts: {str(e)}"
        )


# ============================================================================
# Get Alert Counts
# ============================================================================

@router.get("/counts", response_model=dict)
async def get_counts(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get alert counts grouped by severity and acknowledgment status.
    
    Useful for dashboard widgets showing alert summary.
    
    **Response:**
    ```json
    {
        "total": 100,
        "unacknowledged": 25,
        "acknowledged": 75,
        "by_severity": {
            "critical": 5,
            "error": 3,
            "warning": 12,
            "info": 5
        }
    }
    ```
    """
    try:
        counts = await get_alert_counts(db, user_id=user_id)
        return counts
        
    except Exception as e:
        logger.exception(f"❌ Failed to get alert counts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert counts: {str(e)}"
        )


# ============================================================================
# Get Single Alert
# ============================================================================

@router.get("/{alert_id}", response_model=dict)
async def get_single_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get a single alert by ID.
    
    **Response:**
    ```json
    {
        "id": 1,
        "alert_type": "anomaly_detected",
        "severity": "warning",
        "title": "High anomaly count detected",
        "message": "Sample P5_F10_CD81 has 150 anomalous events (15.0%)",
        "source": "fcs_analysis",
        "sample_id": 42,
        "sample_name": "P5_F10_CD81",
        "metadata": {
            "anomaly_count": 150,
            "threshold": 3.0,
            "affected_channels": ["FSC-A", "SSC-A"]
        },
        "is_acknowledged": false,
        "created_at": "2025-12-31T10:30:00Z"
    }
    ```
    """
    try:
        alert = await get_alert_by_id(db, alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        return alert.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to get alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )


# ============================================================================
# Acknowledge Alert
# ============================================================================

@router.post("/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_single_alert(
    alert_id: int,
    acknowledged_by: Optional[int] = Body(None, description="User ID of acknowledger"),
    notes: Optional[str] = Body(None, description="Acknowledgment notes"),
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Acknowledge an alert.
    
    Marks the alert as reviewed and optionally adds notes.
    
    **Request Body:**
    ```json
    {
        "acknowledged_by": 1,
        "notes": "Reviewed and determined to be within acceptable range"
    }
    ```
    
    **Response:**
    ```json
    {
        "message": "Alert acknowledged",
        "alert": { ... }
    }
    ```
    """
    try:
        alert = await acknowledge_alert(
            db,
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
            notes=notes,
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        return {
            "message": "Alert acknowledged",
            "alert": alert.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


# ============================================================================
# Acknowledge Multiple Alerts
# ============================================================================

@router.post("/acknowledge-multiple", response_model=dict)
async def acknowledge_alerts_batch(
    alert_ids: List[int] = Body(..., description="List of alert IDs to acknowledge"),
    acknowledged_by: Optional[int] = Body(None, description="User ID of acknowledger"),
    notes: Optional[str] = Body(None, description="Acknowledgment notes"),
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Acknowledge multiple alerts at once.
    
    Useful for bulk acknowledgment from dashboard.
    
    **Request Body:**
    ```json
    {
        "alert_ids": [1, 2, 3, 4, 5],
        "acknowledged_by": 1,
        "notes": "Bulk acknowledged during morning review"
    }
    ```
    
    **Response:**
    ```json
    {
        "message": "Acknowledged 5 alerts",
        "acknowledged_count": 5
    }
    ```
    """
    try:
        if not alert_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="alert_ids must not be empty"
            )
        
        count = await acknowledge_multiple_alerts(
            db,
            alert_ids=alert_ids,
            acknowledged_by=acknowledged_by,
            notes=notes,
        )
        
        return {
            "message": f"Acknowledged {count} alerts",
            "acknowledged_count": count,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to acknowledge multiple alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alerts: {str(e)}"
        )


# ============================================================================
# Delete Alert
# ============================================================================

@router.delete("/{alert_id}", response_model=dict)
async def delete_single_alert(
    alert_id: int,
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Delete an alert.
    
    **Response:**
    ```json
    {
        "message": "Alert deleted",
        "alert_id": 1
    }
    ```
    """
    try:
        deleted = await delete_alert(db, alert_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        return {
            "message": "Alert deleted",
            "alert_id": alert_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to delete alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )


# ============================================================================
# Create Alert (Internal/Admin Use)
# ============================================================================

@router.post("/", response_model=dict)
async def create_new_alert(
    alert_type: str = Body(..., description="Alert type"),
    severity: str = Body(..., description="Alert severity (info, warning, critical, error)"),
    title: str = Body(..., description="Alert title"),
    message: str = Body(..., description="Alert message"),
    source: str = Body(..., description="Source of alert"),
    sample_id: Optional[int] = Body(None, description="Related sample ID"),
    user_id: Optional[int] = Body(None, description="User ID"),
    sample_name: Optional[str] = Body(None, description="Sample name for display"),
    metadata: Optional[dict] = Body(None, description="Additional metadata"),
    current_user: dict | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new alert (typically used internally during analysis).
    
    **Request Body:**
    ```json
    {
        "alert_type": "anomaly_detected",
        "severity": "warning",
        "title": "High anomaly count detected",
        "message": "Sample P5_F10_CD81 has 150 anomalous events (15.0%)",
        "source": "fcs_analysis",
        "sample_id": 42,
        "sample_name": "P5_F10_CD81",
        "metadata": {
            "anomaly_count": 150,
            "threshold": 3.0
        }
    }
    ```
    """
    try:
        # Validate severity
        if severity not in ["info", "warning", "critical", "error"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}. Must be one of: info, warning, critical, error"
            )
        
        alert = await create_alert(
            db,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            sample_id=sample_id,
            user_id=user_id,
            sample_name=sample_name,
            metadata=metadata,
        )
        
        return {
            "message": "Alert created",
            "alert": alert.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Failed to create alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )
