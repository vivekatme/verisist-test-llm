#!/usr/bin/env python3
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR
import numpy as np

# Read PDF
with open('test-docs/Apollo247_251863663_labreport.pdf', 'rb') as f:
    file_bytes = f.read()

# Extract OCR
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
images = convert_from_bytes(file_bytes, dpi=300)

all_text = []
for i, img in enumerate(images, 1):
    img_array = np.array(img)
    result = ocr.ocr(img_array, cls=True)

    if result and result[0]:
        for line in result[0]:
            if line[1] and line[1][0]:
                all_text.append(line[1][0])

# Search for missing parameters
print('=== Searching for TRIGLYCERIDES ===')
for i, line in enumerate(all_text):
    if 'TRIGLYCERIDE' in line.upper():
        # Show context (3 lines before and after)
        start = max(0, i-3)
        end = min(len(all_text), i+4)
        for j in range(start, end):
            prefix = '>>> ' if j == i else '    '
            print(f'{prefix}{all_text[j]}')
        print()

print('\n=== Searching for LDL/HDL RATIO or LDL_HDL_RATIO ===')
for i, line in enumerate(all_text):
    upper = line.upper()
    if ('LDL' in upper and 'HDL' in upper and 'RATIO' in upper) or 'LDL/HDL' in upper or 'LDL_HDL' in upper:
        # Show context
        start = max(0, i-3)
        end = min(len(all_text), i+4)
        for j in range(start, end):
            prefix = '>>> ' if j == i else '    '
            print(f'{prefix}{all_text[j]}')
        print()
