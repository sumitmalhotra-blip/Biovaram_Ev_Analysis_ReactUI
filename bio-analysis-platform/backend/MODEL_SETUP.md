# TensorFlow CNN Model Setup Guide

## Overview

The Bio Analysis Platform uses a TensorFlow CNN model (`ev_viability_best_model.h5`) for EV viability classification. This document explains how to configure the model path and troubleshoot loading issues.

---

## Model Path Resolution

The backend uses a priority-based system to locate the model:

### 1. **Environment Variable: `MODEL_PATH` (Recommended)**
```bash
export MODEL_PATH=/path/to/ev_viability_best_model.h5
```
- Absolute or relative paths
- Highest priority
- Use this for production deployments

### 2. **Legacy Environment Variable: `CNN_MODEL_PATH`**
```bash
export CNN_MODEL_PATH=/path/to/ev_viability_best_model.h5
```
- Backwards compatible
- Only checked if `MODEL_PATH` is not set

### 3. **Default Fallback Path**
```
./models/ev_viability_best_model.h5
```
- Relative to the current working directory
- Used if both `MODEL_PATH` and `CNN_MODEL_PATH` are blank

---

## Recommended Folder Structure

### Development Setup
```
bio-analysis-platform/
├── backend/
│   ├── services/
│   │   └── tem/
│   │       ├── ev_viability_best_model.h5        ← bundled model
│   │       ├── shape_classifier.py
│   │       └── tem_analyzer.py
│   ├── models/                                   ← (optional) alternative location
│   │   └── ev_viability_best_model.h5
│   ├── config.py
│   ├── .env.example
│   └── .env                                      ← (not committed to git)
└── frontend/
```

### Production Setup (Recommended)
```
/app/
├── resources/
│   └── models/                                   ← centralized models directory
│       └── ev_viability_best_model.h5
├── backend/
│   ├── services/
│   │   └── tem/
│   │       └── (other code)
│   └── .env
└── frontend/
```

In production, set:
```bash
export MODEL_PATH=/app/resources/models/ev_viability_best_model.h5
```

---

## Configuration Examples

### Example 1: Using `.env` file (Recommended)
```bash
# backend/.env
MODEL_PATH=./models/ev_viability_best_model.h5
```

Then run from the backend directory:
```bash
cd backend
python main.py
```

### Example 2: Using environment variable
```bash
export MODEL_PATH=/usr/local/models/ev_viability_best_model.h5
cd backend
python main.py
```

### Example 3: Bundled model (no configuration needed)
If the model is at `backend/services/tem/ev_viability_best_model.h5`, leave both env vars blank:
```bash
# backend/.env
MODEL_PATH=
CNN_MODEL_PATH=

# Then set your working directory to backend/
cd backend
python main.py
```

---

## Troubleshooting

### Error: "CNN model not found at: ..."

**Cause:** The model file path does not exist.

**Solution:**
1. Verify the model file exists:
   ```bash
   ls -la /path/to/ev_viability_best_model.h5
   ```

2. Check your environment variables:
   ```bash
   echo $MODEL_PATH
   echo $CNN_MODEL_PATH
   ```

3. Verify your working directory matches the path configuration:
   ```bash
   pwd
   # If paths are relative, ensure cwd is correct
   ```

4. Update `.env` with the correct path:
   ```bash
   # Example: model in backend/models/ directory
   MODEL_PATH=./models/ev_viability_best_model.h5
   ```

### Error: "Failed to load TensorFlow model from ..."

**Cause:** The file exists but TensorFlow cannot load it (corrupted file, wrong format, version mismatch).

**Solution:**
1. Verify the file is a valid H5 model:
   ```python
   import tensorflow as tf
   tf.keras.models.load_model('/path/to/model.h5')
   ```

2. Check TensorFlow/Keras versions:
   ```bash
   python -c "import tensorflow as tf; print(tf.__version__)"
   ```

3. Ensure the model was saved with compatible TensorFlow version:
   ```bash
   # If mismatch, retrain the model with current TensorFlow version
   python backend/services/tem/train_cnn.py
   ```

### Warning: "CNN model path not configured ... Falling back to rule-based analysis"

**Cause:** Neither `MODEL_PATH` nor default path contains a valid model.

**Solution:**
1. The system falls back to rule-based analysis (still functional, just less accurate)
2. To enable CNN analysis:
   - Train a new model: `python backend/services/tem/train_cnn.py`
   - Or place existing model at: `./models/ev_viability_best_model.h5`
   - Or set: `export MODEL_PATH=/path/to/model.h5`

---

## Logging Output

When the backend starts, you'll see debug logs showing the resolved model path:

```
INFO: Using MODEL_PATH env var: /path/to/ev_viability_best_model.h5
DEBUG: ✓ Model path resolved and validated: /path/to/ev_viability_best_model.h5
INFO: ✓ Model loaded successfully from /path/to/ev_viability_best_model.h5
```

If something is wrong:

```
ERROR: CNN model not found at: /path/to/ev_viability_best_model.h5
ERROR: Please ensure the TensorFlow model file exists and is readable.
WARNING: CNN model initialization deferred — will fail on first CNN analysis request
```

---

## Quick Start

### 1. Ensure model exists
```bash
# Check bundled location
ls -la backend/services/tem/ev_viability_best_model.h5

# OR train a new model
cd backend
python services/tem/train_cnn.py
```

### 2. Update `.env`
```bash
# Copy template
cp backend/.env.example backend/.env

# Edit (if using default path, leave MODEL_PATH blank)
nano backend/.env
```

### 3. Run backend
```bash
cd backend
python main.py
```

### 4. Verify model loaded
Check logs for:
```
✓ Model path resolved and validated
✓ Model loaded successfully
```

---

## Related Files

- **Env template:** `backend/.env.example`
- **Model training:** `backend/services/tem/train_cnn.py`
- **Model inference:** `backend/services/tem/infer_ev_classifier.py`
- **Analysis service:** `backend/services/tem/tem_service.py`
- **CNN analyzer:** `backend/services/tem/tem_analyzer_cnn.py`
