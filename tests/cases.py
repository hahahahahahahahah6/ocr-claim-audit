GOOD = [
'from pytesseract import image_to_string\nimage_to_string(img)',
'import pytesseract\npytesseract.image_to_string(img)',
'from pytesseract import image_to_data\nimage_to_data(img)',
'import easyocr\neasyocr.Reader([])',
'import easyocr\nr = easyocr.Reader([])\nr.readtext(img)',
'import easyocr\neasyocr.Reader([]).readtext(img)',
'import paddleocr\npaddleocr.PaddleOCR()',
'import paddleocr\nr = paddleocr.PaddleOCR()\nr.ocr(img)',
'from rapidocr_onnxruntime import RapidOCR\nRapidOCR()',
'from rapidocr_onnxruntime import RapidOCR\nengine = RapidOCR()\nengine(img)',
]
BAD = [
'x = 1', 'import pytesseract', 'from PIL import Image\nImage.open(path)',
'import cv2\ncv2.VideoCapture(0)', 'import cv2\ncv2.threshold(img,0,255,0)',
'reader.readtext(img)', 'reader.ocr(img)', 'text = "hello world"',
'import subprocess\nsubprocess.run(["tesseract", "photo.png"])',
'def image_to_string(img): return "hello"\nimage_to_string(img)',
'class Reader: pass\nReader()',
]
