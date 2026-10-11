import unittest
import json
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from digit_templates import match_digit
from ocr import read_digit


class DigitTemplateTests(unittest.TestCase):
    def test_real_expert_digits_from_frames_not_used_as_templates(self):
        folder=Path(__file__).parent/'fixtures'/'expert-digits'
        samples=json.loads((folder/'sources.json').read_text())
        for sample in samples:
            with self.subTest(digit=sample['value']):
                crop=cv2.imread(str(folder/sample['file']))
                with patch('ocr.pytesseract.image_to_data',return_value={
                    'text':[str(sample['value'])], 'conf':[96]
                }) as engine:
                    result=read_digit(crop)
                self.assertEqual(result['value'],sample['value'])
                if sample['template']:
                    self.assertEqual(result['status'],'template')
                    engine.assert_not_called()
                else:
                    self.assertEqual(result['status'],'read')
                    self.assertEqual(engine.call_count,2)

    def test_known_digits_at_multiple_scales(self):
        folder=Path(__file__).resolve().parents[1]/'assets'/'digits'
        for path in folder.glob('*.png'):
            glyph=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
            expected=int(path.stem.split('-')[0])
            for scale in (1,2):
                with self.subTest(path=path.name,scale=scale):
                    result=match_digit(cv2.resize(glyph,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST))
                    self.assertIsNotNone(result)
                    self.assertEqual(result['value'],expected)

    def test_accepted_template_never_calls_tesseract(self):
        glyph=cv2.imread(str(Path(__file__).resolve().parents[1]/'assets'/'digits'/'7-1.png'),cv2.IMREAD_GRAYSCALE)
        with patch('ocr.prepare_digit',return_value=(glyph,True)), \
             patch('ocr.pytesseract.image_to_data',side_effect=AssertionError('OCR innecesario')):
            self.assertEqual(read_digit(np.zeros((30,30,3),dtype=np.uint8))['value'],7)

    def test_unknown_shape_uses_ocr(self):
        glyph=np.full((48,32),255,dtype=np.uint8)
        cv2.putText(glyph,'8',(3,40),cv2.FONT_HERSHEY_SIMPLEX,1.1,0,2)
        self.assertIsNone(match_digit(glyph))
        with patch('ocr.prepare_digit',return_value=(glyph,True)), \
             patch('ocr.pytesseract.image_to_data',return_value={'text':['8'],'conf':[95]}) as engine:
            self.assertEqual(read_digit(np.zeros((30,30,3),dtype=np.uint8))['value'],8)
            self.assertEqual(engine.call_count,2)
