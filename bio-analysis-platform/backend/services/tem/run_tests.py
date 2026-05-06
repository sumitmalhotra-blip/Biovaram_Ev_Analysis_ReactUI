#!/usr/bin/env python3
import sys, os, cv2, glob, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
import tem_analyzer

files = sorted(glob.glob('Training Data/test*.png'))
print('Image'.ljust(10) + 'Detected'.ljust(10) + 'Final'.ljust(15) + 'Confidence')
print('-' * 50)

for f in files:
    if 'small' in f or 'annotated' in f or 'detection' in f:
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    r = tem_analyzer.analyze_image(img)
    if r['total'] == 0:
        print(os.path.basename(f).replace('.png','').ljust(10) + '0'.ljust(10) + 'no detection')
        continue
    classes = [p['classification'] for p in r['particles']]
    confs   = [p['confidence'] for p in r['particles']]
    majority  = max(set(classes), key=classes.count)
    avg_conf  = round(sum(confs) / len(confs) * 100)
    name      = os.path.basename(f).replace('.png', '')
    print(name.ljust(10) + str(r['total']).ljust(10) + majority.ljust(15) + str(avg_conf) + '%')
