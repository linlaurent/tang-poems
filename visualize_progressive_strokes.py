#!/usr/bin/env python3
"""Progressive stroke order visualization.
Shows each character built up stroke by stroke."""

from __future__ import annotations

from pathlib import Path

from src.stroke_order import get_stroke_order


def create_progressive_svg(char: str, strokes: list[str], output_dir: Path):
    """Create progressive SVG files showing stroke-by-stroke buildup."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # SVG viewBox dimensions (typical for cnchar-data)
    viewbox = "0 0 1000 1000"

    total_strokes = len(strokes)
    for step in range(1, total_strokes + 1):
        # Progressive buildup:
        # Step 1 shows only first stroke, Step N shows first N strokes
        # Step 1: show stroke 1 only (highlighted)
        # Step 2: show strokes 1-2 (stroke 2 highlighted)
        # Step N: show strokes 1-N (stroke N highlighted)
        current_strokes = strokes[:step]
        highlighted_stroke_index = step  # 1-indexed: newest stroke is highlighted

        # Create SVG content with horizontal flip + 180-degree rotation
        # SVG transforms apply right-to-left: rotate(180) then flip horizontally
        svg_content = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="{viewbox}"
     width="400"
     height="400"
     style="background-color: #ffffff; border: 1px solid #ddd;">
  <title>{char} - Step {step}/{total_strokes}</title>

  <!-- Group with horizontal flip then 180-degree rotation -->
  <!-- Transforms apply right-to-left: first flip, then rotate -->
  <g transform="rotate(180, 500, 500) translate(1000, 0) scale(-1, 1)">
    <!-- Previous strokes (lighter) -->
"""

        # Add all strokes up to current step
        for i, stroke_path in enumerate(current_strokes, 1):
            # Current stroke is darker, previous strokes are lighter
            if i == highlighted_stroke_index:
                stroke_color = "#000000"  # Black for current stroke
                stroke_width = "3"
            else:
                stroke_color = "#888888"  # Gray for previous strokes
                stroke_width = "2"

            svg_content += (
                f'    <path d="{stroke_path}" fill="none"'
                f' stroke="{stroke_color}"'
                f' stroke-width="{stroke_width}"'
                f' stroke-linecap="round"'
                f' stroke-linejoin="round"/>\n'
            )

        svg_content += f"""\
  </g>

  <!-- Step indicator (not flipped) -->
  <text x="50" y="50" font-family="Arial" font-size="24"
        font-weight="bold" fill="#333">
    {char} - Step {step}/{total_strokes}
  </text>
</svg>
"""

        # Save SVG file
        svg_file = output_dir / f"{char}_step_{step:02d}.svg"
        svg_file.write_text(svg_content, encoding="utf-8")
        print(f"  ✓ Created: {svg_file.name}")

    return len(strokes)


def create_html_viewer(char: str, stroke_count: int, output_dir: Path):
    """Create an HTML file to view all progressive steps."""
    html_content = f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">
    <title>{char} - 笔顺渐进可视化</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        .steps-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .step-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .step-card h3 {{
            margin-top: 0;
            color: #555;
        }}
        .step-card svg {{
            display: block;
            margin: 10px auto;
        }}
    </style>
</head>
<body>
    <h1>字符: {char} - 笔顺渐进可视化</h1>
    <p style="text-align: center; color: #666;">共 {stroke_count} 画</p>

    <div class="steps-container">
"""

    for step in range(1, stroke_count + 1):
        svg_filename = f"{char}_step_{step:02d}.svg"
        html_content += f"""\
        <div class="step-card">
            <h3>步骤 {step}/{stroke_count}</h3>
            <img src="{svg_filename}" alt="Step {step}"
                 style="max-width: 100%; height: auto;">
        </div>
"""

    html_content += """\
    </div>
</body>
</html>
"""

    html_file = output_dir / f"{char}_viewer.html"
    html_file.write_text(html_content, encoding="utf-8")
    print(f"  ✓ Created HTML viewer: {html_file.name}")
    return html_file


def visualize_character(char: str, output_base_dir: Path | None = None):
    """Visualize progressive strokes for a character."""
    if output_base_dir is None:
        output_base_dir = Path("stroke_visualizations")

    print(f"\n{'='*70}")
    print(f"可视化字符: {char}")
    print(f"{'='*70}")

    info = get_stroke_order(char)
    if info is None:
        print(f"❌ 未找到字符 '{char}' 的笔顺数据")
        return None

    stroke_count = info["stroke_count"]
    strokes = info["strokes"]

    # Use strokes in original cnchar-data order (first stroke first)

    print(f"✓ 找到数据: {stroke_count} 画")

    # Create character-specific output directory
    char_output_dir = output_base_dir / char
    print(f"\n生成渐进式 SVG 文件到: {char_output_dir}")

    # Create progressive SVGs
    create_progressive_svg(char, strokes, char_output_dir)

    # Create HTML viewer
    html_file = create_html_viewer(char, stroke_count, char_output_dir)

    print("\n✓ 完成! 打开以下文件查看:")
    print(f"  {html_file.absolute()}")

    return char_output_dir


def main():
    """Main function to visualize 你 and 好."""
    print("=" * 70)
    print("笔顺渐进可视化生成器")
    print("=" * 70)

    output_base = Path("stroke_visualizations")

    chars = ["龍"]

    for char in chars:
        visualize_character(char, output_base)

    print("\n" + "=" * 70)
    print("所有可视化文件已生成")
    print("=" * 70)
    print(f"\n输出目录: {output_base.absolute()}")
    print("\n每个字符包含:")
    print("  - 渐进式 SVG 文件 (step_01.svg, step_02.svg, ...)")
    print("  - HTML 查看器 (viewer.html)")
    print("\n打开 HTML 文件在浏览器中查看渐进式笔顺动画效果")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
