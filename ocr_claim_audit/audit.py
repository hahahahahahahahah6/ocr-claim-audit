"""Offline documentation and AST analysis; audited code is never executed."""
import ast
import fnmatch
import re
from pathlib import Path
from .phrases import OCR, NOOCR

MODULES = {"pytesseract", "easyocr", "paddleocr", "rapidocr_onnxruntime", "rapidocr_openvino", "rapidocr_torch"}
FUNCTIONS = {"pytesseract": {"image_to_string", "image_to_data", "image_to_boxes", "image_to_osd"}, "easyocr": {"Reader"}, "paddleocr": {"PaddleOCR"}, **{m: {"RapidOCR"} for m in MODULES if m.startswith("rapidocr_")}}

def normalize(text):
    return re.sub(r"\s+", " ", text.lower().replace("n't", " not").replace("-", " ")).strip()

def prose(text):
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            mark = match.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and not line.strip()[len(mark):].strip():
                fence = None
            lines.append("")
        elif fence is None:
            lines.append(line)
    return "\n".join(lines)

def claims(text):
    positive = negative = False
    for paragraph in re.split(r"\n\s*\n", prose(text)):
        paragraph = normalize(paragraph)
        for phrase in sorted(NOOCR, key=len, reverse=True):
            paragraph, count = re.subn(r"\b" + re.escape(phrase) + r"\b", " ", paragraph)
            negative |= bool(count)
        positive |= any(re.search(r"\b" + re.escape(p) + r"\b", paragraph) for p in OCR)
    return bool(positive), bool(negative)

def evidence(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    aliases = {}
    shadows = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name in MODULES:
                    aliases[item.asname or item.name] = item.name
        elif isinstance(node, ast.ImportFrom) and node.module in MODULES:
            for item in node.names:
                if item.name in FUNCTIONS[node.module]:
                    aliases[item.asname or item.name] = node.module + "." + item.name
    def resolve(node):
        if isinstance(node, ast.Name):
            return "" if node.id in shadows else aliases.get(node.id, "")
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            return base + "." + node.attr if base else ""
        return ""
    # Every bound/chained reader route necessarily contains its constructor
    # Call in this module, which already satisfies Route B.
    return any(resolve(n.func) in {m + "." + f for m, fs in FUNCTIONS.items() for f in fs}
               for n in ast.walk(tree) if isinstance(n, ast.Call))

def audit(root, ignore=(), fail_on="HIGH"):
    root = Path(root)
    if not root.is_dir():
        raise ValueError("root must be a readable directory")
    pos = neg = prod = test = False
    scanned = 0
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_symlink() or any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts))):
            continue
        if not path.is_file() or any(fnmatch.fnmatch(rel.as_posix(), g) for g in ignore):
            continue
        if path.suffix.lower() == ".md" and (rel.as_posix() == "README.md" or "docs" in rel.parts[:-1]):
            p, n = claims(path.read_text(encoding="utf-8"))
            pos |= p
            neg |= n
        elif path.suffix == ".py":
            if any(p in {"fixtures", "docs", "examples"} for p in rel.parts[:-1]):
                continue
            is_test = "tests" in rel.parts[:-1] or path.name.startswith("test_") or path.name.endswith("_test.py")
            scanned += 1
            found = evidence(path.read_text(encoding="utf-8"))
            if is_test:
                test |= found
            else:
                prod |= found
    findings = []
    if pos and not prod:
        findings.append(dict(rule="documented-ocr-claim-false", severity="MEDIUM" if test else "HIGH", message="Documented picture-word capability lacks production evidence."))
    if neg and prod:
        findings.append(dict(rule="documented-no-ocr-claim-false", severity="HIGH", message="Documented absence conflicts with production evidence."))
    failed = any(f["severity"] == "HIGH" or fail_on == "MEDIUM" for f in findings)
    return dict(verdict="FAIL" if failed else "PASS", findings=findings, scanned_python_files=scanned)
