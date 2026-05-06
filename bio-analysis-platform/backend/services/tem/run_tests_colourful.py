#!/usr/bin/env python3
import sys, os, cv2, glob, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
import tem_analyzer_colourcode_predictions as ta

ta.TEMConfig.BLOB_THRESHOLD  = 0.08
ta.TEMConfig.MIN_DIAMETER_PX = 30

os.makedirs('results/test_annotated', exist_ok=True)

print('Image'.ljust(10) + 'Detected'.ljust(10) + 'Result')
print('-' * 50)

for f in sorted(glob.glob('Training Data/test*.png')):
    if 'annotated' in f or 'detection' in f or 'small' in f:
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    r = ta.analyze_image(img)
    name = os.path.basename(f).replace('.png', '')
    cv2.imwrite('results/test_annotated/' + name + '_annotated.png', r['annotated_image'])
    classes = [p['classification'] for p in r['particles']]
    majority = max(set(classes), key=classes.count) if classes else 'none'
    print(name.ljust(10) + str(r['total']).ljust(10) + majority)
