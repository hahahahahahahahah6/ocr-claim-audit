import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from ocr_claim_audit.audit import audit, claims, evidence
from ocr_claim_audit.__main__ import main
from ocr_claim_audit.phrases import OCR, NOOCR
from tests.cases import GOOD, BAD

ROOT = Path(__file__).resolve().parents[1]

class AuditTests(unittest.TestCase):
    def project(self, doc='Extracts text from images', code=None, name='app.py'):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root/'README.md').write_text(doc)
        if code is not None:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code)
        return root

    def high(self, root, rule='documented-ocr-claim-false'):
        result = audit(root)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertEqual(result['findings'][0]['rule'], rule)

    def test_22_testonly(self):
        for name in ['tests/reader.py', 'test_reader.py', 'reader_test.py']:
            with self.subTest(name=name):
                root = self.project(code=GOOD[0], name=name)
                result = audit(root)
                self.assertEqual(result['verdict'], 'PASS')
                self.assertEqual([f['severity'] for f in result['findings']], ['MEDIUM'])
                self.assertEqual(audit(root, fail_on='MEDIUM')['verdict'], 'FAIL')

    def test_23_negative(self):
        self.high(self.project('No OCR', GOOD[0]), 'documented-no-ocr-claim-false')

    def test_24_no_claim(self):
        self.assertEqual(audit(self.project('Useful tool', GOOD[0]))['findings'], [])

    def test_25_generation(self):
        for doc in ['generates images from text', 'renders text as an image']:
            self.assertEqual(audit(self.project(doc))['findings'], [])

    def test_26_user(self):
        self.assertEqual(audit(self.project('read the text yourself first'))['findings'], [])

    def test_27_bare(self):
        for doc in ['ocr', 'ocr settings', 'Camera capture', 'Image opening and resizing, thresholding, deskewing and file export']:
            self.assertEqual(audit(self.project(doc))['findings'], [])

    def test_28_fences(self):
        for fence in ['```', '~~~~']:
            self.assertEqual(claims(fence+'text\nExtracts text from images\n'+fence), (False, False))

    def test_29_inline(self):
        self.high(self.project('We `extract text from images`.'))

    def test_30_negation(self):
        self.assertEqual(claims("doesn't support ocr"), (False, True))
        self.assertEqual(audit(self.project('does not support ocr'))['findings'], [])

    def test_31_no_source(self):
        self.high(self.project())
        self.assertEqual(audit(self.project('No OCR'))['findings'], [])

    def test_32_self(self):
        self.assertEqual(claims((ROOT/'README.md').read_text()), (False, False))
        self.assertEqual(audit(ROOT)['findings'], [])

    def invoke(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(args)
        return code, out.getvalue()

    def test_33_cli(self):
        self.assertEqual(self.invoke(['--version']), (0, '0.1.0\n'))
        root = self.project(code='x=1')
        code, out = self.invoke([str(root), '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)['verdict'], 'FAIL')
        self.assertEqual(self.invoke([str(root), '--ignore', 'README.md', '--verbose'])[0], 0)
        self.assertEqual(self.invoke([str(root/'missing')])[0], 1)
        self.assertEqual(self.invoke(['--invalid'])[0], 1)
        proc = subprocess.run([sys.executable, '-m', 'ocr_claim_audit', '--version'], capture_output=True, text=True)
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, '0.1.0'))

    def test_34_packaging_and_env(self):
        for file in ['pyproject.toml','MANIFEST.in','README.md','LICENSE','tests/fixtures/.env']:
            self.assertTrue((ROOT/file).is_file())
        self.assertIn('ocr-claim-audit = "ocr_claim_audit.__main__:main"', (ROOT/'pyproject.toml').read_text())
        self.assertIn('MIT License', (ROOT/'LICENSE').read_text())
        self.assertIn('recursive-include tests', (ROOT/'MANIFEST.in').read_text())
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            self.assertNotEqual(path.name, '.env')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded):
            audit(ROOT)
        for folder in ['ocr_claim_audit', 'tests']:
            for path in (ROOT/folder).rglob('*.py'):
                text = path.read_text()
                self.assertIsNone(re.search(r'(?m)^\s*(?:\$\s*)?python\s', text))
                self.assertIsNone(re.search(r'(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36})', text))

    def test_additional_aliases_and_shadowing(self):
        for module, function in [('pytesseract', 'image_to_boxes'), ('pytesseract', 'image_to_osd'), ('easyocr', 'Reader'), ('paddleocr', 'PaddleOCR'), ('rapidocr_openvino', 'RapidOCR'), ('rapidocr_torch', 'RapidOCR')]:
            for code in [f'import {module} as provider\nprovider.{function}(img)', f'from {module} import {function} as run\nrun(img)']:
                self.assertTrue(evidence(code), code)
            self.assertFalse(evidence(f'from {module} import {function}\ndef {function}(*args): pass\n{function}(img)'))
        for code in ['image_to_string(img)', 'readtext(img)', 'ocr(img)', 'engine(img)', 'import cv2\ncv2.imread(path)', 'import cv2\ncv2.resize(img,size)', 'import cv2\ncv2.cvtColor(img,0)', '@app.get("/")\ndef route(): pass', 'class PaddleOCR: pass\nPaddleOCR()', 'class RapidOCR: pass\nRapidOCR()', '# pytesseract.image_to_string(img)\n"easyocr.Reader()"']:
            self.assertFalse(evidence(code), code)

    def test_additional_scope(self):
        for name in ['docs/a.py', 'examples/a.py', 'fixtures/a.py']:
            self.high(self.project(code=GOOD[0], name=name))
        root = self.project(code=GOOD[0], name='excluded.py')
        self.assertEqual(audit(root)['verdict'], 'PASS')
        self.assertEqual(audit(root, ['excluded.py'])['verdict'], 'FAIL')
        (root/'excluded.py').unlink()
        (root/'linked.py').symlink_to(ROOT/'tests/fixtures/good/app.py')
        self.high(root)
        root = self.project('Neutral', GOOD[0])
        (root/'nested/docs').mkdir(parents=True)
        (root/'nested/docs/guide.md').write_text('No OCR')
        self.high(root, 'documented-no-ocr-claim-false')

    def test_additional_normalization(self):
        self.assertEqual(claims('EXTRACTS-TEXT\nFROM IMAGES'), (True, False))
        self.assertEqual(claims('preextracts textually'), (False, False))
        self.assertEqual(claims('No OCR. Also extracts text from images.'), (True, True))
        self.assertEqual(len(audit(self.project('No OCR. Extracts text from images.', GOOD[0]))['findings']), 1)

for index, code in enumerate(GOOD, 1):
    def test(self, code=code):
        self.assertEqual(audit(self.project(code=code))['findings'], [])
    setattr(AuditTests, 'test_%02d_good' % index, test)
for index, code in enumerate(BAD, 11):
    def test(self, code=code):
        self.high(self.project(code=code))
    setattr(AuditTests, 'test_%02d_bad' % index, test)
for index, phrase in enumerate(OCR):
    def test(self, phrase=phrase):
        self.assertEqual(claims(phrase), (True, False))
        self.high(self.project(phrase))
    setattr(AuditTests, 'test_35_positive_%02d' % index, test)
for index, phrase in enumerate(NOOCR):
    def test(self, phrase=phrase):
        self.assertEqual(claims(phrase), (False, True))
        self.assertEqual(audit(self.project(phrase))['findings'], [])
        self.high(self.project(phrase, GOOD[0]), 'documented-no-ocr-claim-false')
    setattr(AuditTests, 'test_35_negative_%02d' % index, test)
