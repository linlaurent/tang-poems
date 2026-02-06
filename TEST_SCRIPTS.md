# Stroke Order Test Scripts

## Progressive Visualization (`visualize_progressive_strokes.py`) ⭐

**Purpose**: Generate progressive stroke-by-stroke visualizations

**Usage**:
```bash
python visualize_progressive_strokes.py
```

**What it does**:
- Creates SVG files showing each step (step 1 = stroke 1, step 2 = strokes 1+2, etc.)
- Generates HTML viewers for easy browsing
- Shows previous strokes in gray, current stroke in black

**Output**:
- `stroke_visualizations/你/` - 7 SVG files + HTML viewer
- `stroke_visualizations/好/` - 6 SVG files + HTML viewer

**Open in browser**:
- `stroke_visualizations/你/你_viewer.html`
- `stroke_visualizations/好/好_viewer.html`

---

## Testing Custom Characters

To test other characters, modify the script to include your character, or use the module directly:

```python
from src.stroke_order import get_stroke_order

info = get_stroke_order("中")
if info:
    print(f"中: {info['stroke_count']} 画")
else:
    print("未找到数据")
```

---

## Module Location

The core module is at: `src/stroke_order.py`

**Key functions**:
- `get_stroke_order(char)` - Get stroke order info for a character
- Returns: `{"char": str, "stroke_count": int, "strokes": List[str]}` or `None`

---

## Data Source

All scripts use data from: `data/cnchar-data/draw/<char>.json`

Make sure the `cnchar-data` dataset is cloned:
```bash
git clone --depth 1 https://github.com/cn-char/cnchar-data.git data/cnchar-data
```
