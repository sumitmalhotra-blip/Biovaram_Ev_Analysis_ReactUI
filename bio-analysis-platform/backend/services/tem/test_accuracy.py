#!/usr/bin/env python3
"""
Batch Accuracy Test — TEM EV Analyzer
======================================
Tests the analyzer on all training images and reports accuracy.

Usage:
    python test_accuracy.py

Folder structure expected:
    trainning_data/viable/       ← intact EV images
    trainning_data/non_viable/   ← non-intact EV images
"""

import sys, os, cv2, glob
sys.path.insert(0, '.')
import tem_analyzer

print('=== VIABLE IMAGES (expected: viable) ===')
v_correct, v_total = 0, 0
for f in sorted(glob.glob('trainning_data/viable/*.png')):
    if 'annotated' in f or 'detection' in f:
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    r = tem_analyzer.analyze_image(img)
    v_correct += r['viable']
    v_total   += r['total']
    acc = r['viable'] / r['total'] * 100 if r['total'] else 0
    print(f"  {os.path.basename(f)[:25]:27s}  viable={r['viable']}/{r['total']}  ({acc:.0f}%)")

print()
print('=== NON-VIABLE IMAGES (expected: non_viable) ===')
nv_correct, nv_total = 0, 0
for f in sorted(glob.glob('trainning_data/non_viable/*.png')):
    if 'annotated' in f or 'detection' in f:
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    r = tem_analyzer.analyze_image(img)
    nv_correct += r['non_viable']
    nv_total   += r['total']
    acc = r['non_viable'] / r['total'] * 100 if r['total'] else 0
    print(f"  {os.path.basename(f)[:25]:27s}  non_viable={r['non_viable']}/{r['total']}  ({acc:.0f}%)")

print()
print('=' * 50)
print(f"Viable accuracy:     {v_correct}/{v_total} ({v_correct/v_total*100:.1f}%)")
print(f"Non-viable accuracy: {nv_correct}/{nv_total} ({nv_correct/nv_total*100:.1f}%)")
total_c = v_correct + nv_correct
total_t = v_total + nv_total
print(f"Overall accuracy:    {total_c}/{total_t} ({total_c/total_t*100:.1f}%)")
print('=' * 50)