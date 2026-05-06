#!/usr/bin/env python3
import sys, os, cv2, glob, re, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
import tem_analyzer

files = sorted(glob.glob('Training Data/test*.png'))
print('Image'.ljust(12) + '  Rule'.ljust(26) + 'CNN'.ljust(26) + 'Nova'.ljust(26) + 'FINAL')
print('-' * 110)

for f in files:
    if 'small' in f or 'annotated' in f or 'detection' in f:
        continue
    img = cv2.imread(f)
    if img is None:
        continue
    r = tem_analyzer.analyze_image(img)
    if r['total'] == 0:
        print(os.path.basename(f).ljust(12) + '  No particles detected')
        continue
    for p in r['particles']:
        confs = re.findall(r'(\w+)=(\w+)\(([\d.]+)\)', p['vote_summary'])
        cm = {c[0]: (c[1], float(c[2])) for c in confs}
        rb   = cm.get('rule_based', ('?', 0))
        cn   = cm.get('cnn', ('?', 0))
        nv   = cm.get('claude', ('?', 0))
        name = os.path.basename(f).ljust(12)
        print(name + '  rule=' + rb[0].ljust(12) + '(' + str(round(rb[1]*100)) + '%)  cnn=' + cn[0].ljust(12) + '(' + str(round(cn[1]*100)) + '%)  nova=' + nv[0].ljust(12) + '(' + str(round(nv[1]*100)) + '%)  FINAL=' + p['classification'].ljust(12) + '(' + str(round(p['confidence']*100)) + '%)')
