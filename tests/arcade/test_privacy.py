"""Privacy (spec 6.5): nothing under arcade/ writes an image, a video, an array dump or a sound file. The only
writers are Sensed and raw scenario records (scenario.ScenarioWriter: base64 and struct), scores, the sessions log
and calibration.json, so the rule has no exemption (record.py uses none).

The rule reads the code with ast, so comments and strings never count: an attribute or a name imwrite, imencode,
VideoWriter, savez (and savez_compressed) or tofile, any attribute .save (np.save, Image.save), and an import of the
module wave. A name wave is allowed (freeze.py's wave(person, ...) is a function)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = frozenset({"imwrite", "imencode", "VideoWriter", "savez", "savez_compressed", "tofile"})


def _wave(module: str | None) -> bool:
    return module == "wave" or (module or "").startswith("wave.")


def forbidden(source: str, filename: str = "<snippet>") -> list[str]:
    """Every forbidden reference in source, as "file:line what"."""
    found = []
    for node in ast.walk(ast.parse(source, filename)):
        where = f"{filename}:{getattr(node, 'lineno', '?')}"
        if isinstance(node, ast.Name) and node.id in FORBIDDEN:
            found.append(f"{where} name {node.id}")
        elif isinstance(node, ast.Attribute) and (node.attr in FORBIDDEN or node.attr == "save"):
            found.append(f"{where} attribute .{node.attr}")
        elif isinstance(node, ast.Import):
            found += [f"{where} import {alias.name}" for alias in node.names if _wave(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and _wave(node.module):
                found.append(f"{where} from {node.module} import")
            found += [f"{where} imports {alias.name}" for alias in node.names if alias.name in FORBIDDEN]
    return found


def test_no_forbidden_calls():
    files = sorted(p for p in (ROOT / "arcade").rglob("*.py") if "__pycache__" not in p.parts)
    assert len(files) >= 40 and ROOT / "arcade" / "sources" / "scenario.py" in files
    found = [hit for path in files for hit in forbidden(path.read_text(), str(path.relative_to(ROOT)))]
    assert not found, "spec 6.5: arcade/ must not write images, video, arrays or sound:\n" + "\n".join(found)


@pytest.mark.parametrize("snippet", [
    "cv2.imwrite(path, frame)",
    "ok, png = cv2.imencode('.png', frame)",
    "out = cv2.VideoWriter(path, fourcc, 30, size)",
    "np.savez(path, frame=frame)",
    "np.savez_compressed(path, frame=frame)",
    "frame.tofile(path)",
    "np.save(path, frame)",
    "Image.fromarray(frame).save(path)",
    "imwrite(path, frame)",
    "from cv2 import imwrite",
    "import wave",
    "import wave as w",
    "from wave import open as wave_open",
    "def f():\n    import wave\n    return wave.open('a.wav', 'wb')",
])
def test_the_rule_catches(snippet):
    assert forbidden(snippet), snippet


@pytest.mark.parametrize("snippet", [
    "def wave(person, start, end):\n    pass\nwave(p, 0.0, 1.0)",
    "self._wave(color)",
    "save_calibration(data_dir, cal)",
    "self.saved = True",
    "text = 'cv2.imwrite and np.save'",
    "# cv2.imwrite(path, frame)\nx = 1",
    "from . import wave",
    "fh.write(line)",
])
def test_the_rule_allows(snippet):
    assert forbidden(snippet) == [], snippet
