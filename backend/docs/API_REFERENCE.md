# API Reference

**BioVaram EV Analysis Platform - REST API Documentation**

*Base URL: `http://localhost:8000/api/v1`*

---

## 📋 Table of Contents

1. [Health & Status](#health--status)
2. [File Upload](#file-upload)
3. [Samples](#samples)
4. [Results](#results)
5. [Authentication](#authentication)

---

## Health & Status

### Check Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T10:30:00Z"
}
```

### Get System Status

```http
GET /api/v1/status
```

**Response:**
```json
{
  "status": "connected",
  "database": "postgresql",
  "version": "1.0.0"
}
```

---

## File Upload

### Upload FCS File

```http
POST /api/v1/upload/fcs
Content-Type: multipart/form-data
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | File | Yes | FCS file to upload |
| `user_id` | string | No | User identifier |

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/fcs" \
  -F "file=@PC3_EXO1.fcs" \
  -F "user_id=user123"
```

**Response (200 OK):**
```json
{
  "success": true,
  "sample_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "PC3_EXO1.fcs",
  "message": "File uploaded and processed successfully",
  "statistics": {
    "total_events": 914326,
    "channel_count": 26,
    "acquisition_date": "17-Dec-2025"
  },
  "size_distribution": {
    "d10": 89.5,
    "d50": 127.3,
    "d90": 198.7,
    "mean": 138.2,
    "std": 45.6
  },
  "histogram": {
    "bins": [50, 60, 70, ...],
    "counts": [1234, 5678, 9012, ...]
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Invalid FCS file format",
  "details": "File does not contain required channels"
}
```

---

### Upload NTA File

```http
POST /api/v1/upload/nta
Content-Type: multipart/form-data
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | File | Yes | NTA text file |
| `user_id` | string | No | User identifier |

**Response:**
```json
{
  "success": true,
  "sample_id": "660e8400-e29b-41d4-a716-446655440001",
  "filename": "sample_size_1.txt",
  "statistics": {
    "d10": 92.1,
    "d50": 135.8,
    "d90": 215.4,
    "concentration": 2.5e9,
    "particle_count": 15234
  },
  "histogram": {
    "bins": [0, 10, 20, ...],
    "counts": [0, 45, 123, ...]
  }
}
```

---

## Samples

### List All Samples

```http
GET /api/v1/samples
```

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `user_id` | string | null | Filter by user |
| `sample_type` | string | null | `fcs` or `nta` |
| `limit` | int | 100 | Max results |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "samples": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "PC3_EXO1.fcs",
      "sample_type": "fcs",
      "upload_date": "2026-01-20T14:30:00Z",
      "event_count": 914326,
      "user_id": "user123"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "filename": "sample_size_1.txt",
      "sample_type": "nta",
      "upload_date": "2026-01-20T15:00:00Z",
      "event_count": 5234,
      "user_id": "user123"
    }
  ],
  "total": 17,
  "limit": 100,
  "offset": 0
}
```

---

### Get Sample Details

```http
GET /api/v1/samples/{sample_id}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "PC3_EXO1.fcs",
  "sample_type": "fcs",
  "upload_date": "2026-01-20T14:30:00Z",
  "file_size_mb": 90.7,
  "event_count": 914326,
  "channel_count": 26,
  "channels": ["FSC-H", "FSC-A", "SSC-H", "SSC-A", ...],
  "acquisition_info": {
    "date": "17-Dec-2025",
    "time": "17:39:14",
    "cytometer": "CytoFLEX nano",
    "operator": "URAT"
  },
  "results_count": 1
}
```

---

### Delete Sample

```http
DELETE /api/v1/samples/{sample_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Sample deleted successfully"
}
```

---

## Results

### Get FCS Results

```http
GET /api/v1/samples/{sample_id}/results/fcs
```

**Response:**
```json
{
  "sample_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "PC3_EXO1.fcs",
  "statistics": {
    "total_events": 914326,
    "valid_events": 912456,
    "outliers_removed": 1870,
    "outlier_percentage": 0.2
  },
  "size_distribution": {
    "d10": 89.5,
    "d50": 127.3,
    "d90": 198.7,
    "mean": 138.2,
    "std": 45.6,
    "mode": 115.0,
    "min": 32.1,
    "max": 489.2
  },
  "scatter_data": {
    "fsc": [1234.5, 2345.6, ...],
    "ssc": [5678.9, 6789.0, ...],
    "size": [102.3, 115.7, ...]
  },
  "histogram": {
    "bins": [50, 60, 70, 80, ...],
    "counts": [1234, 5678, 9012, 7890, ...]
  },
  "calibration": {
    "method": "ssc_calibration",
    "slope": 0.196,
    "intercept": 1.354
  }
}
```

---

### Get NTA Results

```http
GET /api/v1/samples/{sample_id}/results/nta
```

**Response:**
```json
{
  "sample_id": "660e8400-e29b-41d4-a716-446655440001",
  "filename": "sample_size_1.txt",
  "statistics": {
    "particle_count": 15234,
    "concentration": 2.5e9,
    "concentration_unit": "particles/mL"
  },
  "size_distribution": {
    "d10": 92.1,
    "d50": 135.8,
    "d90": 215.4,
    "mean": 148.3,
    "std": 52.1,
    "mode": 125.0
  },
  "histogram": {
    "bins": [0, 10, 20, 30, ...],
    "counts": [0, 45, 123, 456, ...]
  },
  "measurement_info": {
    "temperature": 25.0,
    "viscosity": 0.89,
    "dilution_factor": 500
  }
}
```

---

## Authentication

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user123",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword",
  "name": "Jane Doe"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user456",
    "email": "newuser@example.com",
    "name": "Jane Doe"
  }
}
```

---

## Error Responses

All endpoints return consistent error format:

```json
{
  "success": false,
  "error": "Error type",
  "details": "Detailed error message",
  "code": "ERROR_CODE"
}
```

**Common Error Codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILE` | 400 | Invalid file format |
| `SAMPLE_NOT_FOUND` | 404 | Sample ID doesn't exist |
| `UNAUTHORIZED` | 401 | Invalid or missing token |
| `FORBIDDEN` | 403 | Not allowed to access resource |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Testing with Swagger UI

The API has built-in interactive documentation:

1. Start the backend: `python run_api.py`
2. Open http://localhost:8000/docs
3. Try any endpoint directly in the browser

---

*For implementation details, see `BACKEND_ARCHITECTURE.md`*
