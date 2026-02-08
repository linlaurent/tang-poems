"""Stroke-order widget for Streamlit flashcard mode.

Renders poem content as interactive HTML where double-clicking any Chinese
character opens a modal showing its progressive stroke order.
"""

from __future__ import annotations

import json
import re

from src.stroke_order import get_stroke_order

# Regex matching CJK Unified Ideographs (common + extension A/B)
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff"  # CJK Unified Ideographs
    r"\u3400-\u4dbf"  # CJK Extension A
    r"\U00020000-\U0002a6df"  # CJK Extension B
    r"\uf900-\ufaff"  # CJK Compatibility Ideographs
    r"]"
)


def _is_cjk(ch: str) -> bool:
    """Return True if *ch* is a CJK ideograph."""
    return bool(_CJK_RE.fullmatch(ch))


def _collect_stroke_data(text: str) -> dict[str, list[str]]:
    """Return {char: [svg_path, ...]} for every unique CJK char in *text*.

    Characters are fetched in parallel so the GitHub fallback (used on
    Streamlit Cloud where the local submodule is absent) stays fast.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Deduplicate CJK characters while preserving order
    seen: set[str] = set()
    chars: list[str] = []
    for ch in text:
        if ch not in seen and _is_cjk(ch):
            seen.add(ch)
            chars.append(ch)

    if not chars:
        return {}

    result: dict[str, list[str]] = {}

    # Fetch all characters in parallel (ThreadPool is fine for I/O-bound work)
    with ThreadPoolExecutor(max_workers=min(len(chars), 16)) as pool:
        future_to_char = {pool.submit(get_stroke_order, ch): ch for ch in chars}
        for future in as_completed(future_to_char):
            ch = future_to_char[future]
            try:
                info = future.result()
                if info is not None:
                    result[ch] = info["strokes"]
            except Exception:
                pass  # skip characters that fail

    return result


def _wrap_chars(text: str, stroke_data: dict[str, list[str]]) -> str:
    """Wrap each CJK character in an interactive <span>.

    Non-CJK characters (punctuation, whitespace, etc.) pass through as-is.
    Newlines are converted to ``<br>``.
    """
    parts: list[str] = []
    for ch in text:
        if ch == "\n":
            parts.append("<br>")
        elif _is_cjk(ch):
            cls = "stroke-char" if ch in stroke_data else "stroke-char-nodata"
            parts.append(f'<span class="{cls}" data-char="{ch}">{ch}</span>')
        else:
            parts.append(ch)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Self-contained HTML template
# ---------------------------------------------------------------------------

_CSS = """\
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
}
/* Poem card */
.poem-widget {
    padding: 1.5rem;
    border-radius: 10px;
    background-color: #f8f9fa;
    margin: 0;
    border-left: 4px solid #4CAF50;
    font-size: 1.2rem;
    line-height: 2;
    color: #34495e;
    white-space: pre-line;
}
.poem-widget .stroke-char {
    cursor: pointer;
    border-radius: 3px;
    transition: background 0.15s;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}
.poem-widget .stroke-char:hover {
    background: #e8f5e9;
}
.poem-widget .stroke-char-nodata {
    /* no stroke data available – no hover effect */
}
.hint-line {
    text-align: center;
    font-size: 0.8rem;
    color: #999;
    margin-top: 0.6rem;
}
.show-all-btn {
    display: block;
    margin: 0.6rem auto 0;
    padding: 6px 18px;
    font-size: 0.9rem;
    background: #4CAF50;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
}
.show-all-btn:hover { background: #388E3C; }
/* All-characters layout inside modal */
.char-section { margin-bottom: 22px; }
.char-section-header {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 6px;
    border-bottom: 1px solid #eee;
    padding-bottom: 4px;
}
.char-section-header .char-count {
    font-size: 0.85rem;
    font-weight: normal;
    color: #888;
    margin-left: 8px;
}

/* Modal overlay */
.stroke-modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    z-index: 9999;
    justify-content: center;
    align-items: center;
}
.stroke-modal-overlay.open {
    display: flex;
}
.stroke-modal {
    background: #fff;
    border-radius: 12px;
    padding: 24px 28px 20px;
    max-width: 90vw;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    position: relative;
    /* width/height set dynamically by JS based on stroke count */
}
.stroke-modal-close {
    position: absolute;
    top: 10px;
    right: 14px;
    font-size: 1.6rem;
    cursor: pointer;
    color: #888;
    background: none;
    border: none;
    line-height: 1;
}
.stroke-modal-close:hover { color: #333; }
.stroke-modal h2 {
    margin: 0 0 4px;
    font-size: 1.5rem;
}
.stroke-modal .subtitle {
    color: #888;
    font-size: 0.95rem;
    margin-bottom: 14px;
}
.stroke-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
}
.stroke-step {
    text-align: center;
    background: #fafafa;
    border-radius: 8px;
    padding: 8px 4px 6px;
    border: 1px solid #eee;
}
.stroke-step .step-label {
    font-size: 0.75rem;
    color: #666;
    margin-bottom: 2px;
}
"""

_JS = """\
(function() {
  var STROKE_DATA = __STROKE_JSON__;

  var overlay = document.getElementById('strokeModalOverlay');
  var modal   = document.getElementById('strokeModal');

  var poemWidget  = document.querySelector('.poem-widget');
  var hintLine    = document.querySelector('.hint-line');
  var showAllBtn  = document.getElementById('showAllStrokesBtn');

  /* Expand iframe to cover parent viewport so modal is page-centered */
  function expandFrame() {
    /* Hide poem content so it doesn't shift visually */
    if (poemWidget) poemWidget.style.visibility = 'hidden';
    if (hintLine)   hintLine.style.visibility   = 'hidden';
    if (showAllBtn) showAllBtn.style.visibility  = 'hidden';

    var frame = window.frameElement;
    if (frame) {
      frame._origStyle = frame.style.cssText;
      frame.style.position = 'fixed';
      frame.style.top = '0';
      frame.style.left = '0';
      frame.style.width = '100vw';
      frame.style.height = '100vh';
      frame.style.zIndex = '999999';
    }
  }
  function restoreFrame() {
    var frame = window.frameElement;
    if (frame && frame._origStyle !== undefined) {
      frame.style.cssText = frame._origStyle;
    }

    /* Restore poem content visibility */
    if (poemWidget) poemWidget.style.visibility = '';
    if (hintLine)   hintLine.style.visibility   = '';
    if (showAllBtn) showAllBtn.style.visibility  = '';
  }

  /* Close helpers */
  function closeModal() {
    overlay.classList.remove('open');
    restoreFrame();
  }
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeModal();
  });
  document.getElementById('strokeModalClose').addEventListener('click', closeModal);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
  });

  /* Build one SVG step (returns SVG string) */
  function buildSVG(strokes, step) {
    var paths = '';
    for (var i = 0; i < step; i++) {
      var isHighlighted = (i === step - 1);
      var color  = isHighlighted ? '#000000' : '#888888';
      var sw     = isHighlighted ? 3 : 2;
      paths += '<path d="' + strokes[i] + '" fill="none"'
             + ' stroke="' + color + '"'
             + ' stroke-width="' + sw + '"'
             + ' stroke-linecap="round"'
             + ' stroke-linejoin="round"/>';
    }
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"'
         + ' width="110" height="110"'
         + ' style="background:#fff;border:1px solid #ddd;border-radius:6px;">'
         + '<g transform="rotate(180,500,500) translate(1000,0) scale(-1,1)">'
         + paths + '</g></svg>';
  }

  /* Helper: populate modal for a single character */
  function showSingleChar(ch) {
    var strokes = STROKE_DATA[ch];
    if (!strokes) return;

    document.getElementById('strokeModalTitle').textContent = ch;
    document.getElementById('strokeModalSubtitle').textContent =
      '共 ' + strokes.length + ' 画';

    var n = strokes.length;
    var w;
    if (n <= 4)       { w = 40; }
    else if (n <= 8)  { w = 55; }
    else if (n <= 12) { w = 70; }
    else              { w = 85; }
    modal.style.width  = w + 'vw';
    modal.style.height = 'auto';

    var grid = document.getElementById('strokeGrid');
    grid.innerHTML = '';
    for (var s = 1; s <= strokes.length; s++) {
      var div = document.createElement('div');
      div.className = 'stroke-step';
      div.innerHTML = '<div class="step-label">' + s + '/' + strokes.length + '</div>'
                    + buildSVG(strokes, s);
      grid.appendChild(div);
    }
    expandFrame();
    overlay.classList.add('open');
  }

  /* Double-click handler */
  document.querySelectorAll('.stroke-char').forEach(function(span) {
    span.addEventListener('dblclick', function(e) {
      e.preventDefault();
      showSingleChar(this.getAttribute('data-char'));
    });
  });

  /* "Show All Strokes" button */
  document.getElementById('showAllStrokesBtn').addEventListener('click', function() {
    /* Collect unique CJK chars in document order */
    var chars = [];
    var seen = {};
    document.querySelectorAll('.stroke-char').forEach(function(span) {
      var ch = span.getAttribute('data-char');
      if (!seen[ch] && STROKE_DATA[ch]) { seen[ch] = true; chars.push(ch); }
    });
    if (!chars.length) return;

    document.getElementById('strokeModalTitle').textContent = '全部笔顺';
    document.getElementById('strokeModalSubtitle').textContent =
      '共 ' + chars.length + ' 个汉字';

    modal.style.width  = '88vw';
    modal.style.height = 'auto';

    var grid = document.getElementById('strokeGrid');
    grid.innerHTML = '';
    /* Reset grid to single-column for all-characters view */
    grid.style.display = 'block';

    for (var ci = 0; ci < chars.length; ci++) {
      var ch = chars[ci];
      var strokes = STROKE_DATA[ch];

      var section = document.createElement('div');
      section.className = 'char-section';

      var header = document.createElement('div');
      header.className = 'char-section-header';
      header.innerHTML = ch + '<span class="char-count">'
        + strokes.length + ' 画</span>';
      section.appendChild(header);

      var subgrid = document.createElement('div');
      subgrid.className = 'stroke-grid';
      for (var s = 1; s <= strokes.length; s++) {
        var div = document.createElement('div');
        div.className = 'stroke-step';
        div.innerHTML = '<div class="step-label">' + s + '/' + strokes.length + '</div>'
                      + buildSVG(strokes, s);
        subgrid.appendChild(div);
      }
      section.appendChild(subgrid);
      grid.appendChild(section);
    }

    expandFrame();
    overlay.classList.add('open');

    /* Restore grid display on close so single-char view works again */
    var origClose = closeModal;
    closeModal = function() {
      grid.style.display = '';
      origClose();
      closeModal = origClose;
    };
    /* Re-bind overlay click & close button & Escape for this session */
    overlay.onclick = function(e) { if (e.target === overlay) closeModal(); };
    document.getElementById('strokeModalClose').onclick = closeModal;
  });
})();
"""


def render_poem_with_strokes(content: str) -> str:
    """Return a self-contained HTML string for displaying *content*.

    Each CJK character is interactive: double-click opens a modal showing
    progressive stroke order (if data is available).
    """
    stroke_data = _collect_stroke_data(content)
    wrapped_content = _wrap_chars(content, stroke_data)

    # Serialise stroke data for embedding in JS
    stroke_json = json.dumps(stroke_data, ensure_ascii=False)

    js_block = _JS.replace("__STROKE_JSON__", stroke_json)

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>{_CSS}</style></head>
<body>
<div class="poem-widget">{wrapped_content}</div>
<div class="hint-line">双击任意汉字查看笔顺</div>
<button class="show-all-btn" id="showAllStrokesBtn">✍️ 全部笔顺</button>

<!-- Modal -->
<div class="stroke-modal-overlay" id="strokeModalOverlay">
  <div class="stroke-modal" id="strokeModal">
    <button class="stroke-modal-close" id="strokeModalClose">&times;</button>
    <h2 id="strokeModalTitle"></h2>
    <div class="subtitle" id="strokeModalSubtitle"></div>
    <div class="stroke-grid" id="strokeGrid"></div>
  </div>
</div>

<script>{js_block}</script>
</body>
</html>
"""
    return html
