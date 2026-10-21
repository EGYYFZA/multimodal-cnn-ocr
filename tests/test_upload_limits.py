"""Check endpoint read limits without loading ML models or external dependencies."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        super().__init__(detail)


class Upload:
    def __init__(self, size):
        self.size = size
        self.requested = None

    async def read(self, size=-1):
        self.requested = size
        return b'x' * (self.size if size < 0 else min(size, self.size))


source = Path(__file__).parents[1] / 'apps/api/app/routes/predict.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
endpoint = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'predict')
endpoint.decorator_list = []
namespace = {
    'UploadFile': Upload, 'File': lambda value: value, 'Form': lambda value: value,
    'HTTPException': HTTPException,
    'settings': SimpleNamespace(max_upload_mb=1, max_text_chars=100),
}
exec(compile(ast.Module(body=[endpoint], type_ignores=[]), str(source), 'exec'), namespace)


class UploadLimitTests(unittest.TestCase):
    def test_exact_limit_reaches_ocr(self):
        class ReachedOCR(Exception):
            pass

        def check_image(data):
            self.assertEqual(len(data), 1024 * 1024)
            raise ReachedOCR

        with patch.dict(namespace, {'ocr_image_bytes': check_image}):
            with self.assertRaises(ReachedOCR):
                asyncio.run(namespace['predict'](image_file=Upload(1024 * 1024)))

    def test_oversized_files_are_rejected_after_bounded_read(self):
        for field in ('image_file', 'video_file'):
            with self.subTest(field=field):
                upload = Upload(2 * 1024 * 1024)
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(namespace['predict'](**{field: upload}))
                self.assertEqual(raised.exception.status_code, 413)
                self.assertEqual(upload.requested, 1024 * 1024 + 1)

    def test_long_text_is_rejected_before_reading_upload(self):
        upload = Upload(1)
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(namespace['predict'](title='x' * 101, image_file=upload))
        self.assertEqual(raised.exception.status_code, 413)
        self.assertIsNone(upload.requested)

    def test_ocr_agreement_uses_existing_evidence_without_name_error(self):
        import sys
        from types import ModuleType

        preprocess = ModuleType('app.services.preprocess')
        preprocess.clean_text = lambda text: text
        dependencies = {
            'ocr_image_bytes': lambda data: 'example news text',
            'merge_inputs': lambda *parts: ' '.join(parts),
            'search_similar': lambda *args, **kwargs: [{'label_dataset': '0'}],
            'predict_proba': lambda *args, **kwargs: 0.2,
            'model_info': lambda: {'output_mode': 'sigmoid'},
            'decide_label': lambda prob, tau: 'HOAKS' if prob >= tau else 'VALID',
            'get_confidence_level': lambda *args: 'test',
            'append_log': lambda entry: None,
            'JSONResponse': lambda data: data,
            'settings': SimpleNamespace(max_upload_mb=1, max_text_chars=100, operating_tau=0.45),
        }
        with patch.dict(namespace, dependencies), patch.dict(sys.modules, {'app.services.preprocess': preprocess}):
            result = asyncio.run(namespace['predict'](image_file=Upload(1)))
        self.assertEqual(result['label'], 'VALID')
        self.assertTrue(result['used_ocr'])


if __name__ == '__main__':
    unittest.main()
