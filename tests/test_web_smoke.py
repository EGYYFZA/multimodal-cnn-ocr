"""Exercise the real web stack without loading thesis models or running OCR."""
import io
import os
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image


class WebSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_cwd = Path.cwd()
        api = Path(__file__).resolve().parents[1] / 'apps/api'
        sys.path.insert(0, str(api))
        os.chdir(api)
        doubles = {}
        functions = {
            'model_service': {
                'load_model_on_startup': lambda: None,
                'model_info': lambda: {'output_mode': 'sigmoid'},
                'predict_proba': lambda *a, **k: 0.2,
                'decide_label': lambda *a: 'VALID',
                'get_confidence_level': lambda *a: 'test',
            },
            'dataset_service': {
                'load_datasets_on_startup': lambda: None,
                'dataset_stats': lambda: {},
                'search_similar': lambda *a, **k: [],
            },
            'ocr_service': {
                'ocr_image_bytes': lambda data: '',
                'ocr_video_bytes': lambda data: ('', 0),
            },
            'preprocess': {
                'clean_text': lambda text: text,
                'merge_inputs': lambda *parts: ' '.join(parts).strip(),
            },
            'log_service': {'append_log': lambda entry: None},
        }
        for name, members in functions.items():
            module = ModuleType('app.services.' + name)
            module.__dict__.update(members)
            doubles[module.__name__] = module
        cls.patches = patch.dict(sys.modules, doubles)
        cls.patches.start()
        from app.main import create_app
        cls.client = TestClient(create_app())

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.patches.stop()
        os.chdir(cls.previous_cwd)
        sys.path.pop(0)

    def test_home_template_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>Deteksi Berita Hoaks</title>', response.text)

    def test_empty_form_remains_supported(self):
        response = self.client.post('/api/predict', data={'title': '', 'body': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['label'], 'NO_TEXT')

    def test_long_text_is_rejected_through_real_form_parser(self):
        response = self.client.post('/api/predict', data={'title': 'x' * 12001})
        self.assertEqual(response.status_code, 413)

    def test_png_upload_passes_through_real_multipart_parser(self):
        image = io.BytesIO()
        Image.new('RGB', (2, 2)).save(image, format='PNG')
        payload = image.getvalue()
        with Image.open(io.BytesIO(payload)) as decoded:
            decoded.load()
            self.assertEqual(decoded.size, (2, 2))
        response = self.client.post('/api/predict', files={'image_file': ('image.png', payload, 'image/png')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['label'], 'NO_TEXT')


if __name__ == '__main__':
    unittest.main()
