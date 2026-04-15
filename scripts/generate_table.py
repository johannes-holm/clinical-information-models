#!/usr/bin/env python3

import json
import csv
import sys
import glob
from pathlib import Path

INPUT_DIR = "fsh-generated/resources"
OUTPUT_DIR_INCLUDES = "input/includes"
OUTPUT_DIR_CSV = "input/images/generated"


def load_sd(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


#Mudelite indekseerimine, et oleks võimalik navigeerida teistesse viidatud mudelitesse
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

# Loendite indekseerimine, et oleks võimalik navigeerida tabeli vaatest otse IMis kasutavasse loendisse
def build_vs_index():
    index = {}
    files = glob.glob(f"{INPUT_DIR}/ValueSet-*.json")
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            resource = json.load(f)
        if resource.get('resourceType') == 'ValueSet':
            vid = resource.get('id', '')
            url = resource.get('url', '')
            if url and vid:
                index[url] = vid
    return index

#Tuvastab tüübi ja olukorras, kus viidatakse teisele IMle, tagastab selle mudeli ID
def get_type_info(types_array, model_index):
    if not types_array:
        return {'code': '', 'display': '', 'is_ref': False, 'ref_id': None}

    t = types_array[0]
    code = t.get('code', '')
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


#Loendi kasuamise korral tagastab selle asukoha (lingib)
def get_binding_info(elem, vs_index):
    binding = elem.get('binding', {})
    if not binding:
        return {'display': '', 'vs_id': None, 'vs_url': '', 'strength': ''}

    vs_url = binding.get('valueSet', '')
    strength = binding.get('strength', '')

    # Eemalda versioon URL-ist
    clean_url = vs_url.split('|')[0] if '|' in vs_url else vs_url

    # Kuvanimi
    vs_name = clean_url.split('/')[-1] if '/' in clean_url else clean_url

    # Kontrolli kas lokaalne VS
    vs_id = vs_index.get(clean_url)

    return {
        'display': vs_name,
        'vs_id': vs_id,
        'vs_url': clean_url,
        'strength': strength
    }


def get_example(elem):
    examples = elem.get('example', [])
    if examples and isinstance(examples, list):
        ex = examples[0]
        for suffix in ['valueString', 'valueCode', 'valueInteger',
                       'valueBoolean', 'valueDate', 'valueDateTime']:
            if suffix in ex:
                return str(ex[suffix])
    return ''


#SD-selementide parsimine
def parse_elements(sd, model_index, vs_index):
    snapshot_elems = sd.get('snapshot', {}).get('element')
    diff_elems = sd.get('differential', {}).get('element')
    elements = snapshot_elems or diff_elems or []

    if not elements:
        print(f"Elemendid puuduvad {sd.get('id', '?')}", file=sys.stderr)
        return []

    root_type = sd.get('type', sd.get('id', ''))
    rows = []

    for elem in elements:
        path = elem.get('path', '')
        parts = path.split('.')

        if len(parts) <= 1:
            continue

        types = elem.get('type', [])
        type_info = get_type_info(types, model_index)
        vs_info = get_binding_info(elem, vs_index)

        depth = len(parts) - 2
        field_name = parts[-1]

        min_c = int(elem.get('min', 0))
        max_c = str(elem.get('max', '*'))

        if min_c >= 1:
            required = 'Jah'
        else:
            required = 'Ei'

        if max_c == '*':
            repetition = 'Korduv'
        elif max_c == '0':
            repetition = 'Ei kasutata'
        else:
            repetition = 'Ei ole korduv'

        row = {
            'depth': depth,
            'field_name': field_name,
            'full_path': path.replace(root_type + '.', ''),
            'description': elem.get('short', elem.get('definition', '')),
            'required': required,
            'cardinality': f'{min_c}..{max_c}',
            'repetition': repetition,
            'type_display': type_info['display'],
            'type_code': type_info['code'],
            'type_is_ref': type_info['is_ref'],
            'type_ref_id': type_info['ref_id'],
            'vs_info': vs_info,
            'comment': elem.get('comment', ''),
            'example': get_example(elem),
        }
        rows.append(row)

    return rows


#  XHTML väljund fail
def escape_html(text):
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def write_xhtml(rows, output_path, title=""):
    if not rows:
        return

    indent_unit = '&nbsp;&nbsp;&nbsp;&nbsp;'

    lines = [
        f'<!-- Auto-generated table for {escape_html(title)} -->',
        '<table class="grid">',
        '  <thead>',
        '    <tr>',
        '      <th>Andmeelement</th>',
        '      <th>Kirjeldus</th>',
        '      <th>Kohustuslik</th>',
        '      <th>Kardinaalsus</th>',
        '      <th>Andmetuup</th>',
        '      <th>Loend</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>',
    ]

    for row in rows:
        indent = indent_unit * row['depth']
        name = escape_html(row['field_name'])
        # veerud 
        # Element 
        if row['type_code'] == 'BackboneElement' or row['type_code'] == '':
            display_name = f'{indent}<b>{name}</b>'
        elif row['required'] == 'Jah':
            display_name = f'{indent}<b>{name}</b>'
        else:
            display_name = f'{indent}{name}'

        # Kohustuslikkus
        if row['required'] == 'Jah':
            req_display = '<span style="color:#d32f2f">Jah</span>'
        else:
            req_display = 'Ei'

        # Andmetüüp (koos lingiga kui viidatakse tesiele IMle)
        if row['type_is_ref'] and row['type_ref_id']:
            ref_id = row['type_ref_id']
     
            type_cell = (
                f'<a href="model-{escape_html(ref_id.lower())}.html">'
                f'{escape_html(row["type_display"])}</a>'
            )
        elif row['type_display']:
            type_cell = f'<code>{escape_html(row["type_display"])}</code>'
        else:
            type_cell = ''

        # Loendid (koos lingiga)
        vs = row['vs_info']
        if vs.get('display'):
            if vs.get('vs_id'):
                # Lokaalselt defineeritud loend ehk link IG sees
                vs_cell = (
                    f'<a href="ValueSet-{escape_html(vs["vs_id"])}.html">'
                    f'{escape_html(vs["display"])}</a>'
                )
            elif vs.get('vs_url'):
                # Väline loend ehk link mingile muule URLile
                vs_cell = (
                    f'<a href="{escape_html(vs["vs_url"])}" target="_blank">'
                    f'{escape_html(vs["display"])}</a>'
                )
            else:
                vs_cell = escape_html(vs['display'])

            # Lisa strength
            if vs.get('strength'):
                vs_cell += f' ({escape_html(vs["strength"])})'
        else:
            vs_cell = ''

        # Rea koostamine 
        lines.append('    <tr>')
        lines.append(f'      <td>{display_name}</td>')
        lines.append(f'      <td>{escape_html(row["description"])}</td>')
        lines.append(f'      <td>{req_display}</td>')
        lines.append(f'      <td><code>{row["cardinality"]}</code></td>')
        lines.append(f'      <td>{type_cell}</td>')
        lines.append(f'      <td>{vs_cell}</td>')
        lines.append('    </tr>')

    lines.extend([
        '  </tbody>',
        '</table>',
    ])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def write_csv(rows, output_path):
    if not rows:
        return

    fieldnames = [
        'Tase', 'Andmeelement', 'Andmeelement (t\u00e4israda)', 'Kirjeldus',
        'Kohustuslik', 'Kardinaalsus', 'Korduvus', 'Andmetuup',
        'Loend', 'Selgitus', 'Naide'
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in rows:
            indent_str = '  ' * row['depth']
            vs = row['vs_info']
            vs_display = vs.get('display', '')
            if vs.get('strength'):
                vs_display += f' ({vs["strength"]})'

            writer.writerow({
                'Tase': row['depth'] + 1,
                'Andmeelement': f'{indent_str}{row["field_name"]}',
                'Andmeelement (t\u00e4israda)': row['full_path'],
                'Kirjeldus': row['description'],
                'Kohustuslik': row['required'],
                'Kardinaalsus': row['cardinality'],
                'Korduvus': row['repetition'],
                'Andmetuup': row['type_display'],
                'Loend': vs_display,
                'Selgitus': row['comment'],
                'Naide': row['example'],
            })



def process_file(filepath, model_index, vs_index):
    sd = load_sd(filepath)

    if sd.get('resourceType') != 'StructureDefinition':
        return None
    if sd.get('kind') != 'logical':
        return None

    model_id = sd.get('id', 'unknown')
    title = sd.get('title', sd.get('name', model_id))


    rows = parse_elements(sd, model_index, vs_index)

    if not rows:
        print(f"Elemente ei leitud", file=sys.stderr)
        return None

    xhtml_path = f"{OUTPUT_DIR_INCLUDES}/generated-table-{model_id}.xhtml"
    write_xhtml(rows, xhtml_path, title=title)
    print(f"    XHTML: {xhtml_path}")

    csv_path = f"{OUTPUT_DIR_CSV}/{model_id}-table.csv"
    write_csv(rows, csv_path)
    print(f"    CSV:   {csv_path}")

    return model_id


def batch_mode():
    # Ehita indeksid ENNE töötlemist
    model_index = build_model_index()
    vs_index = build_vs_index()
    print(f"Loogilisi mudeleid: {len(set(model_index.values()))}")
    print(f"Lokaalseid ValueSet-e: {len(set(vs_index.values()))}")

    Path(OUTPUT_DIR_INCLUDES).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR_CSV).mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(f"{INPUT_DIR}/StructureDefinition-*.json"))

    count = 0
    for filepath in files:
        result = process_file(filepath, model_index, vs_index)
        if result:
            count += 1

    print(f"\nTabeleid loodud: {count}")


def main():
    if len(sys.argv) == 1:
        batch_mode()
    else:
        print("Kasutus: python generate_table.py")


if __name__ == '__main__':
    main()