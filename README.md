# ocr-claim-audit 0.1.0

Offline static checking of documented picture-word claims against Python source.
No provider installation is needed; audited code is never executed.
Requires Python 3.9 or newer. MIT licensed.

## Usage

```sh
python3 -m pip install .
ocr-claim-audit /path/to/project --json
python3 -m ocr_claim_audit /path/to/project --verbose
python3 -m ocr_claim_audit /path/to/project --ignore 'docs/generated/*' --fail-on MEDIUM
python3 -m unittest discover
python3 -m build
```

The default threshold is HIGH. MEDIUM findings remain visible but exit zero;
`--fail-on MEDIUM` makes them fail. Exit codes are 0 for PASS, 2 for FAIL,
and 1 for usage or filesystem errors. `--version` prints 0.1.0.
JSON includes verdict, findings (rule, severity, message), and a source count.
At most one finding appears per family. Rule identifiers:

```text
documented-ocr-claim-false
documented-no-ocr-claim-false
```

## Scope

Root README.md and Markdown beneath any docs path component supply claims.
Fenced blocks are excluded; inline code counts. Paragraph lines are joined,
case folded, contractions expanded, hyphens replaced with spaces, and whitespace
collapsed. Matching uses word boundaries and exact templates. Negative spans
are removed first, longest first.

Production evidence comes from AST calls resolved through provider imports and
aliases: pytesseract image_to_string, image_to_data, image_to_boxes, image_to_osd;
easyocr Reader; paddleocr PaddleOCR; and RapidOCR from rapidocr_onnxruntime,
rapidocr_openvino, or rapidocr_torch. Reader construction alone counts, so
bound and chained calls also qualify. Local function/class names shadow imports.
Source under tests or with test file names supplies only MEDIUM evidence.
Source under fixtures, docs, and examples, and symlinked files, is excluded.
Environment files are never opened.

## Limitations

Only the exact templates below count. A bare acronym or settings heading is
insufficient. Opposite-direction image generation, camera capture, image
opening, preprocessing, file export, and instructions for the user to inspect
words themselves are outside claim scope. Imports, strings, decorators,
unbound reader methods, pixel processing, and image loading are insufficient.
A subprocess invoking a system reader helper is excluded: command strings do
not establish a provider call. Other recognition stacks, including phone-camera
SDKs, cloud picture-word APIs, and handwriting-specific engines, are out of
scope. Only the Python routes listed above count. Static analysis cannot prove
runtime success, dependency availability, or image quality. Invalid syntax
provides no evidence. Files must be UTF-8. With no source, a positive claim
fails at HIGH while a negative claim passes. No claims always passes.

## Exact vocabulary

```text
extracts text from scanned documents
extract text from scanned documents
supports optical character recognition
support optical character recognition
extracts text from screenshots
extract text from screenshots
recognizes text from images
recognize text from images
recognises text from images
recognise text from images
recognizes text in images
recognize text in images
recognises text in images
recognise text in images
extracts text from images
extract text from images
extracts text from photos
extract text from photos
reads text from images
read text from images
reads text from photos
read text from photos
reads text in images
read text in images
converts images to text
convert images to text
converts photos to text
convert photos to text
performs ocr on images
perform ocr on images
performs ocr on photos
perform ocr on photos
optical character recognition support
does ocr on images
do ocr on images
recognizes text
recognize text
recognises text
recognise text
extracts text
extract text
reads text
read text
ocr support
supports ocr
support ocr
text recognition
optical character recognition
does not support optical character recognition
does not recognize text in images
does not recognise text in images
does not recognize text from images
does not recognise text from images
does not extract text from images
does not extract text from photos
does not read text from images
does not read text from photos
does not convert images to text
does not convert photos to text
does not perform ocr on images
does not perform ocr
does not support ocr
optical character recognition not supported
text recognition not supported
ocr not supported
no optical character recognition
without optical character recognition
no text recognition
without text recognition
no ocr support
without ocr support
no ocr
without ocr
```
