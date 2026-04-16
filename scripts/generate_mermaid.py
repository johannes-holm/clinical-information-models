#!/usr/bin/env python3
"""
Generates SVG class diagrams from FHIR Logical Model StructureDefinitions.
Outputs inline SVG in XHTML includes — zero external dependencies.
"""

import json
import sys
import re
import glob
from pathlib import Path
from collections import defaultdict

INPUT_DIR = "fsh-generated/resources"
OUTPUT_DIR_INCLUDES = "input/includes"
OUTPUT_DIR_IMAGES = "input/images/generated"


def load_structure_definition(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


def get_display_name(path):
    return path.split('.')[-1] if '.' in path else path


def build_model_index():
    index = {}
    files = glob.glob(f"{INPUT_DIR}/StructureDefinition-*.json")
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            sd = json.load(f)
        if (sd.get('resourceType') == 'StructureDefinition'
                and sd.get('kind') == 'logical'):
            mid = sd.get('id', '')
            for key in [sd.get('url', ''), sd.get('type', '')]:
                if key:
                    index[key] = mid
    return index


def get_type_info(types_array, model_index):
    if not types_array:
        return {'code': 'Element', 'display': 'Element',
                'is_ref': False, 'ref_id': None}
    t = types_array[0]
    code = t.get('code', 'Element')
    profiles = t.get('profile', []) or []
    target_profiles = t.get('targetProfile', []) or []

    for p in profiles + target_profiles:
        if p in model_index:
            return {'code': code, 'display': model_index[p],
                    'is_ref': True, 'ref_id': model_index[p]}
    if code in model_index:
        return {'code': code, 'display': model_index[code],
                'is_ref': True, 'ref_id': model_index[code]}

    return {'code': code, 'display': code,
            'is_ref': False, 'ref_id': None}


def parse_elements(sd, model_index):
    snapshot_elems = sd.get('snapshot', {}).get('element')
    diff_elems = sd.get('differential', {}).get('element')
    elements = snapshot_elems or diff_elems or []

    classes = defaultdict(lambda: {
        'title': '',
        'description': '',
        'fields': [],
        'children': [],
        'references': []
    })

    for elem in elements:
        path = elem.get('path', '')
        parts = path.split('.')

        if len(parts) == 1:
            classes[path]['title'] = get_display_name(path)
            classes[path]['description'] = elem.get('short',
                                            elem.get('definition', path))
            continue

        short = elem.get('short', elem.get('definition', parts[-1]))
        min_card = elem.get('min', 0)
        max_card = elem.get('max', '*')
        cardinality = f"{min_card}..{max_card}"

        types = elem.get('type', [])
        type_info = get_type_info(types, model_index)

        parent_path = '.'.join(parts[:-1])
        field_name = parts[-1]

        if type_info['is_ref']:
            classes[parent_path]['references'].append({
                'name': field_name,
                'ref_id': type_info['ref_id'],
                'cardinality': cardinality,
                'short': short
            })
        elif type_info['code'] == 'BackboneElement':
            classes[path]['title'] = field_name
            classes[path]['description'] = short
            classes[parent_path]['children'].append({
                'path': path,
                'name': field_name,
                'cardinality': cardinality,
                'short': short
            })
        else:
            classes[parent_path]['fields'].append({
                'name': field_name,
                'type': type_info['display'],
                'cardinality': cardinality,
                'short': short,
                'required': min_card is not None and int(min_card) > 0
            })

    return classes


def escape_svg(text):
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def measure_text(text, font_size=13):
    return len(text) * font_size * 0.62


def generate_svg(sd, model_index):
    """Generate an SVG class diagram with proper layout."""
    classes = parse_elements(sd, model_index)
    root_name = sd.get('name', sd.get('id', 'Model'))

    # ── Layout constants ──
    FONT_SIZE = 13
    HEADER_FONT_SIZE = 14
    LINE_HEIGHT = 22
    HEADER_HEIGHT = 32
    PADDING_X = 12
    PADDING_Y = 10
    BOX_MIN_WIDTH = 220
    BOX_GAP_Y = 50
    BOX_GAP_X = 120
    CORNER_RADIUS = 6

    # ── Colors ──
    COLORS = {
        'root':  {'header': '#2563eb', 'body': '#eff6ff', 'border': '#2563eb'},
        'child': {'header': '#059669', 'body': '#ecfdf5', 'border': '#059669'},
        'ref':   {'header': '#d97706', 'body': '#fffbeb', 'border': '#d97706'},
    }
    HEADER_TEXT = '#ffffff'
    FIELD_TEXT = '#1f2937'
    REQUIRED_TEXT = '#dc2626'
    ARROW_COLOR = '#6b7280'
    REF_ARROW_COLOR = '#d97706'

    # ──────────────────────────────────────────
    #  STEP 1: Build boxes for real classes
    # ──────────────────────────────────────────
    main_boxes = []       # root + BackboneElement children
    box_by_path = {}      # path → box lookup

    for path, cls_data in classes.items():
        is_root = '.' not in path
        display = cls_data['title'] or get_display_name(path)
        fields = cls_data['fields']

        field_texts = []
        for f in fields:
            req = '\u25cf ' if f['required'] else '\u25cb '
            text = f'{req}{f["type"]} {f["name"]} [{f["cardinality"]}]'
            field_texts.append(text)

        max_text_width = measure_text(display, HEADER_FONT_SIZE)
        for ft in field_texts:
            w = measure_text(ft, FONT_SIZE)
            if w > max_text_width:
                max_text_width = w

        box_width = max(BOX_MIN_WIDTH, int(max_text_width + PADDING_X * 2 + 10))
        num_fields = len(fields)
        box_height = HEADER_HEIGHT + PADDING_Y * 2
        if num_fields > 0:
            box_height += num_fields * LINE_HEIGHT
        else:
            box_height += LINE_HEIGHT

        box = {
            'path': path,
            'display': display,
            'fields': fields,
            'field_texts': field_texts,
            'children': cls_data['children'],
            'references': cls_data['references'],
            'width': box_width,
            'height': box_height,
            'is_root': is_root,
            'is_ref': False,
            'x': 0, 'y': 0,
        }
        main_boxes.append(box)
        box_by_path[path] = box

    # ──────────────────────────────────────────
    #  STEP 2: Collect ALL references (including from children)
    # ──────────────────────────────────────────
    # arrow_list: [{source_path, ref_id, ref_name, cardinality}, ...]
    arrow_list = []
    unique_ref_ids = []

    for box in main_boxes:
        for ref in box['references']:
            ref_id = ref['ref_id']
            arrow_list.append({
                'source_path': box['path'],
                'ref_id': ref_id,
                'name': ref['name'],
                'cardinality': ref['cardinality'],
            })
            if ref_id not in unique_ref_ids:
                unique_ref_ids.append(ref_id)

    # ──────────────────────────────────────────
    #  STEP 3: Create reference boxes (one per unique ref)
    # ──────────────────────────────────────────
    ref_boxes = []
    for ref_id in unique_ref_ids:
        ref_display = ref_id
        ref_width = max(BOX_MIN_WIDTH,
                        int(measure_text(ref_display, HEADER_FONT_SIZE) + PADDING_X * 2 + 10))
        ref_box = {
            'path': ref_id,
            'display': ref_display,
            'fields': [],
            'field_texts': [],
            'children': [],
            'references': [],
            'width': ref_width,
            'height': HEADER_HEIGHT + LINE_HEIGHT + PADDING_Y,
            'is_root': False,
            'is_ref': True,
            'ref_id': ref_id,
            'x': 0, 'y': 0,
        }
        ref_boxes.append(ref_box)
        box_by_path[ref_id] = ref_box

    # ──────────────────────────────────────────
    #  STEP 4: Position main column (left side)
    # ──────────────────────────────────────────
    main_x = 40
    y_cursor = 30
    main_max_width = 0

    for box in main_boxes:
        box['x'] = main_x
        box['y'] = y_cursor
        y_cursor += box['height'] + BOX_GAP_Y
        if box['width'] > main_max_width:
            main_max_width = box['width']

    main_column_bottom = y_cursor

    # ──────────────────────────────────────────
    #  STEP 5: Position reference column (right side)
    #  Each ref gets its own y-position, no overlaps
    # ──────────────────────────────────────────
    if ref_boxes:
        ref_x = main_x + main_max_width + BOX_GAP_X

        # Calculate ideal y for each ref box:
        # Average y-center of all source boxes pointing to it
        for ref_box in ref_boxes:
            source_y_centers = []
            for arrow in arrow_list:
                if arrow['ref_id'] == ref_box['path']:
                    src = box_by_path.get(arrow['source_path'])
                    if src:
                        source_y_centers.append(src['y'] + src['height'] / 2)
            if source_y_centers:
                ideal_center = sum(source_y_centers) / len(source_y_centers)
                ref_box['_ideal_y'] = ideal_center - ref_box['height'] / 2
            else:
                ref_box['_ideal_y'] = 30

        # Sort by ideal y
        ref_boxes.sort(key=lambda b: b['_ideal_y'])

        # Place with collision avoidance
        min_y = 30
        for ref_box in ref_boxes:
            desired_y = max(ref_box['_ideal_y'], min_y)
            ref_box['x'] = ref_x
            ref_box['y'] = desired_y
            min_y = desired_y + ref_box['height'] + 30  # gap between refs

    # ──────────────────────────────────────────
    #  STEP 6: Calculate SVG dimensions
    # ──────────────────────────────────────────
    all_boxes = main_boxes + ref_boxes
    if all_boxes:
        svg_width = max(b['x'] + b['width'] for b in all_boxes) + 60
        svg_height = max(b['y'] + b['height'] for b in all_boxes) + 40
    else:
        svg_width = 500
        svg_height = 200

    svg_width = max(svg_width, 500)
    svg_height = max(svg_height, 200)

    # ──────────────────────────────────────────
    #  BUILD SVG
    # ──────────────────────────────────────────
    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'style="max-width:{svg_width}px;width:100%;height:auto;'
        f'font-family:Segoe UI,Roboto,Arial,sans-serif;">'
    )

    # Defs
    svg.append('  <defs>')
    svg.append(
        '    <marker id="arrow" viewBox="0 0 10 10" '
        'refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{ARROW_COLOR}"/>'
        '</marker>'
    )
    svg.append(
        '    <marker id="arrow-ref" viewBox="0 0 10 10" '
        'refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{REF_ARROW_COLOR}"/>'
        '</marker>'
    )
    svg.append(
        '    <filter id="shadow" x="-4%" y="-4%" width="108%" height="108%">'
        '<feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.12"/>'
        '</filter>'
    )
    svg.append('  </defs>')
    svg.append('')

    # ── DRAW CHILD ARROWS (main column, top to bottom) ──
    for box in main_boxes:
        for child in box['children']:
            target = box_by_path.get(child['path'])
            if not target:
                continue

            x1 = box['x'] + box['width'] // 2
            y1 = box['y'] + box['height']
            x2 = target['x'] + target['width'] // 2
            y2 = target['y']
            mid_y = (y1 + y2) // 2

            svg.append(
                f'  <path d="M{x1},{y1} L{x1},{mid_y} L{x2},{mid_y} L{x2},{y2}" '
                f'fill="none" stroke="{ARROW_COLOR}" stroke-width="1.5" '
                f'marker-end="url(#arrow)"/>'
            )

            label = f'[{child["cardinality"]}]'
            label_w = len(label) * 7 + 12
            label_x = (x1 + x2) // 2
            svg.append(
                f'  <rect x="{label_x - label_w//2}" y="{mid_y - 12}" '
                f'width="{label_w}" height="17" rx="3" '
                f'fill="white" stroke="{ARROW_COLOR}" stroke-width="0.5"/>'
            )
            svg.append(
                f'  <text x="{label_x}" y="{mid_y + 1}" '
                f'text-anchor="middle" font-size="11" fill="{ARROW_COLOR}">'
                f'{label}</text>'
            )

    # ── DRAW REFERENCE ARROWS (left to right, each one unique) ──
    # Track y-offsets on target side to prevent arrow endpoint overlap
    ref_arrow_offsets = defaultdict(int)

    for arrow in arrow_list:
        src = box_by_path.get(arrow['source_path'])
        tgt = box_by_path.get(arrow['ref_id'])
        if not src or not tgt:
            continue

        # Source: right edge, spaced vertically per reference
        src_ref_count = len(src['references'])
        src_ref_idx = next(
            (i for i, r in enumerate(src['references'])
             if r['ref_id'] == arrow['ref_id'] and r['name'] == arrow['name']),
            0
        )
        # Spread connection points along the right edge of source box
        if src_ref_count > 1:
            src_y_start = src['y'] + HEADER_HEIGHT + 10
            src_y_end = src['y'] + src['height'] - 10
            src_y_step = (src_y_end - src_y_start) / max(src_ref_count - 1, 1)
            y1 = src_y_start + src_ref_idx * src_y_step
        else:
            y1 = src['y'] + src['height'] // 2

        x1 = src['x'] + src['width']

        # Target: left edge, offset each arrow slightly
        offset = ref_arrow_offsets[arrow['ref_id']]
        ref_arrow_offsets[arrow['ref_id']] += 18
        x2 = tgt['x']
        y2 = tgt['y'] + HEADER_HEIGHT // 2 + offset

        # Clamp y2 within target box
        y2 = min(y2, tgt['y'] + tgt['height'] - 5)
        y2 = max(y2, tgt['y'] + 5)

        # Draw curved arrow
        mid_x = (x1 + x2) // 2
        svg.append(
            f'  <path d="M{x1},{y1} C{mid_x},{y1} {mid_x},{y2} {x2},{y2}" '
            f'fill="none" stroke="{REF_ARROW_COLOR}" stroke-width="1.5" '
            f'stroke-dasharray="6,3" marker-end="url(#arrow-ref)"/>'
        )

        # Arrow label (positioned along the curve)
        label = f'{escape_svg(arrow["name"])} [{arrow["cardinality"]}]'
        label_w = len(label) * 7 + 12
        label_x = mid_x
        label_y = (y1 + y2) // 2

        svg.append(
            f'  <rect x="{label_x - label_w//2}" y="{label_y - 12}" '
            f'width="{label_w}" height="17" rx="3" '
            f'fill="white" stroke="{REF_ARROW_COLOR}" stroke-width="0.5"/>'
        )
        svg.append(
            f'  <text x="{label_x}" y="{label_y + 1}" '
            f'text-anchor="middle" font-size="11" fill="{REF_ARROW_COLOR}">'
            f'{label}</text>'
        )

    svg.append('')

    # ── DRAW BOXES (on top of arrows) ──
    for box in all_boxes:
        x, y, w, h = box['x'], box['y'], box['width'], box['height']

        if box['is_ref']:
            colors = COLORS['ref']
        elif box.get('is_root'):
            colors = COLORS['root']
        else:
            colors = COLORS['child']

        clip_id = f'clip-{sanitize_name(box["path"])}'

        # Clickable wrapper for ref boxes
        if box['is_ref']:
            ref_id = box.get('ref_id', box['path'])
            svg.append(
                f'  <a xlink:href="model-{ref_id.lower()}.html" target="_top">'
            )

        # Box body with shadow
        svg.append(
            f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{CORNER_RADIUS}" fill="{colors["body"]}" '
            f'stroke="{colors["border"]}" stroke-width="2" '
            f'filter="url(#shadow)"/>'
        )

        # Clipping path for header corners
        svg.append(
            f'  <clipPath id="{clip_id}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{CORNER_RADIUS}"/></clipPath>'
        )

        # Header background
        svg.append(
            f'  <rect x="{x}" y="{y}" width="{w}" height="{HEADER_HEIGHT}" '
            f'fill="{colors["header"]}" clip-path="url(#{clip_id})"/>'
        )

        # Header text
        svg.append(
            f'  <text x="{x + w // 2}" y="{y + HEADER_HEIGHT // 2 + 5}" '
            f'text-anchor="middle" fill="{HEADER_TEXT}" '
            f'font-weight="bold" font-size="{HEADER_FONT_SIZE}">'
            f'{escape_svg(box["display"])}</text>'
        )

        # Separator line
        svg.append(
            f'  <line x1="{x}" y1="{y + HEADER_HEIGHT}" '
            f'x2="{x + w}" y2="{y + HEADER_HEIGHT}" '
            f'stroke="{colors["border"]}" stroke-width="1"/>'
        )

        # Fields
        if box['field_texts']:
            for i, ft in enumerate(box['field_texts']):
                fy = y + HEADER_HEIGHT + PADDING_Y + (i * LINE_HEIGHT) + 14
                field = box['fields'][i]
                color = REQUIRED_TEXT if field['required'] else FIELD_TEXT
                svg.append(
                    f'  <text x="{x + PADDING_X}" y="{fy}" '
                    f'fill="{color}" font-size="{FONT_SIZE}">'
                    f'{escape_svg(ft)}</text>'
                )
        elif box['is_ref']:
            fy = y + HEADER_HEIGHT + PADDING_Y + 14
            svg.append(
                f'  <text x="{x + w // 2}" y="{fy}" '
                f'text-anchor="middle" fill="{colors["header"]}" '
                f'font-size="12" font-style="italic">'
                f'\u00ab Infomudel \u00bb</text>'
            )

        # Close link
        if box['is_ref']:
            svg.append('  </a>')

        svg.append('')

    svg.append('</svg>')
    return '\n'.join(svg)


# ──────────────────────────────────────────────────────────────
#  FILE PROCESSING
# ──────────────────────────────────────────────────────────────
def process_file(filepath, model_index, output_mmd=None, output_xhtml=None):
    sd = load_structure_definition(filepath)

    if sd.get('resourceType') != 'StructureDefinition':
        return None
    if sd.get('kind') != 'logical':
        return None

    model_id = sd.get('id', 'unknown')

    # Generate inline SVG
    svg_code = generate_svg(sd, model_index)

    # Save XHTML include with inline SVG
    if output_xhtml:
        Path(output_xhtml).parent.mkdir(parents=True, exist_ok=True)
        xhtml = (
            f'<!-- Auto-generated diagram for {model_id} -->\n'
            f'{svg_code}\n'
        )
        Path(output_xhtml).write_text(xhtml, encoding='utf-8')
        print(f"  SVG:   {output_xhtml}")

    # Also save standalone SVG file
    if output_mmd:
        svg_path = output_mmd.replace('.mmd', '.svg')
        Path(svg_path).parent.mkdir(parents=True, exist_ok=True)
        Path(svg_path).write_text(svg_code, encoding='utf-8')
        print(f"  File:  {svg_path}")

    return svg_code


def batch_mode():
    model_index = build_model_index()
    print(f"Loogilisi mudeleid: {len(set(model_index.values()))}")

    Path(OUTPUT_DIR_INCLUDES).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR_IMAGES).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{INPUT_DIR}/StructureDefinition-*.json"))

    count = 0
    for filepath in files:
        model_id = Path(filepath).stem.replace('StructureDefinition-', '')
        result = process_file(
            filepath,
            model_index,
            output_mmd=f"{OUTPUT_DIR_IMAGES}/{model_id}.mmd",
            output_xhtml=f"{OUTPUT_DIR_INCLUDES}/generated-mermaid-{model_id}.xhtml"
        )
        if result:
            count += 1

    print(f"Diagramme loodud: {count}")


def main():
    if len(sys.argv) == 1:
        batch_mode()
    else:
        print("Kasutus: python generate_mermaid.py")


if __name__ == '__main__':
    main()