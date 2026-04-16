#!/usr/bin/env python3

import json
import sys
import re
import glob
from pathlib import Path
from collections import defaultdict


# - Kust võetakse info ning kuhu kaustadesse diagrammid paigutatakse
INPUT_DIR = "fsh-generated/resources"
OUTPUT_DIR_INCLUDES = "input/includes"
OUTPUT_DIR_IMAGES = "input/images/generated"


# Kui Sushi käsk on tehtud on vajalik lugeda SD jsonina
def load_structure_definition(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# Eemaldada erisümbolid mermaidi jaoks (vastasel juhul ei ehita ära)
def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# Viimane element on displayName (juurelementide jaoks vajalik)
def get_display_name(path):
    return path.split('.')[-1] if '.' in path else path


#Ehitab mapingu, kuidas liikuda urlist mudeli IDni
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

#Tuvastab elemendi tüübi ning kui element on reference teisele mudelile, siis tagastab, ka mudeli ID
def get_type_info(types_array, model_index):
 
    if not types_array:
        return {'code': 'Element', 'display': 'Element',
                'is_ref': False, 'ref_id': None}

    t = types_array[0]
    code = t.get('code', 'Element')
    profiles = t.get('profile', []) or []
    target_profiles = t.get('targetProfile', []) or []

    # Kontrolli profiile esmalt
    for p in profiles + target_profiles:
        if p in model_index:
            return {'code': code, 'display': model_index[p],
                    'is_ref': True, 'ref_id': model_index[p]}

    # Kontrolli code ennast (loogilistel mudelitel on code = URL)
    if code in model_index:
        return {'code': code, 'display': model_index[code],
                'is_ref': True, 'ref_id': model_index[code]}

    return {'code': code, 'display': code,
            'is_ref': False, 'ref_id': None}


# Struktureerib SD jsoni hierarhiliseks struktuuriks (esialgu proovib snapshotti, fallback on differential)
def parse_elements(sd, model_index):
    snapshot_elems = sd.get('snapshot', {}).get('element')
    diff_elems = sd.get('differential', {}).get('element')
    elements = snapshot_elems or diff_elems or []

    if not elements:
        print(f"Elemente ei leitud {sd.get('id', '?')}", file=sys.stderr)

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
            classes[path]['description'] = elem.get('short', elem.get('definition', path))
            continue

        # elementide omadused
        short = elem.get('short', elem.get('definition', parts[-1]))
        min_card = elem.get('min', 0)
        max_card = elem.get('max', '*')
        cardinality = f"{min_card}..{max_card}"

        # andmetüüpide tuvastamine
        types = elem.get('type', [])
        type_info = get_type_info(types, model_index)

        parent_path = '.'.join(parts[:-1])
        field_name = parts[-1]

        # Backbone element tähendab alamklassi, vastasel juhul tavalised elemenitde omadused
        if type_info['is_ref']:
            # Viide teisele infomudelile 
            classes[parent_path]['references'].append({
                'name': field_name,
                'ref_id': type_info['ref_id'],
                'cardinality': cardinality,
                'short': short
            })
        elif type_info['code'] == 'BackboneElement':
            # Inline alamklass 
            classes[path]['title'] = field_name
            classes[path]['description'] = short
            classes[parent_path]['children'].append({
                'path': path,
                'name': field_name,
                'cardinality': cardinality,
                'short': short
            })
        else:
            # Tavaline väli 
            classes[parent_path]['fields'].append({
                'name': field_name,
                'type': type_info['display'],
                'cardinality': cardinality,
                'short': short,
                'required': min_card is not None and int(min_card) > 0
            })

    return classes


def generate_mermaid(sd, model_index):
    classes = parse_elements(sd, model_index)
    root_name = sd.get('name', sd.get('id', 'Model'))
    current_model_id = sd.get('id', root_name)

    lines = ['classDiagram','']

    reference_models = set()
    for path, cls_data in classes.items():
        safe_name = sanitize_name(path)
    

        lines.append(f'  class {safe_name} {{')

        for field in cls_data['fields']:
             lines.append(f'+{field["type"]} {field["name"]} [{field["cardinality"]}]')

        lines.append('  }')
        lines.append('')

        for child in cls_data['children']:
            child_safe = sanitize_name(child['path'])
            lines.append(f'{safe_name} --> "{child["cardinality"]}" 'f'{child_safe} : {child["name"]}')

         # Viited teistele infomudelitele 
        for ref in cls_data['references']:
            ref_id = ref['ref_id']
            ref_safe = sanitize_name(ref_id)

        
            if ref_id not in reference_models:
                lines.append(f'  class {ref_safe}')
                lines.append('')
                lines.append(
                    f'  click {ref_safe} href '
                    f'"model-{ref_id.lower()}.html"'
                )
                lines.append('')
                reference_models.add(ref_id)

            lines.append(
                f'  {safe_name} --> "{ref["cardinality"]}" '
                f'{ref_safe} : {ref["name"]}'
            )

    lines.append('')

    return '\n'.join(lines)


# Viib eelnevad funktsioonid kokku 
def process_file(filepath, model_index, output_mmd=None, output_xhtml=None):
    sd = load_structure_definition(filepath)

    if sd.get('resourceType') != 'StructureDefinition':
        return None
    if sd.get('kind') != 'logical':
        return None

    model_id = sd.get('id', 'unknown')
    mermaid_code = generate_mermaid(sd, model_index)

    # Save .mmd file (will be rendered to SVG by mmdc)
    if output_mmd:
        Path(output_mmd).parent.mkdir(parents=True, exist_ok=True)
        Path(output_mmd).write_text(mermaid_code, encoding='utf-8')
        print(f"  Mermaid: {output_mmd}")

    # Save XHTML include — references SVG image, NO scripts
    if output_xhtml:
        Path(output_xhtml).parent.mkdir(parents=True, exist_ok=True)
        xhtml = (
            f'<!-- Auto-generated diagram for {model_id} -->\n'
            f'<div>\n'
            f'  <img src="generated/{model_id}.svg" '
            f'alt="{model_id} klassidiagramm" '
            f'style="max-width:100%"/>\n'
            f'</div>\n'
        )
        Path(output_xhtml).write_text(xhtml, encoding='utf-8')

    return mermaid_code

#Töötleb kõik SD failid, mis eksisteerivad fsh-generated/resources
def batch_mode():

    model_index = build_model_index()
    print(f"Leitud loogilisi mudeleid indeksis: {len(set(model_index.values()))}")

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


    print(f"Diagramme loogilistest mudelistest loodud: {count}")



# Testimiseks saab ühe faili kaupa ka genereerida diagramme (IG avalikustamisena ei mängi rolli)
"""
def single_file_mode(input_path: str, output_path: str = None):
    
    sd = load_structure_definition(input_path)
    mermaid = generate_mermaid(sd)

    if output_path:
        Path(output_path).write_text(mermaid, encoding='utf-8')
        print(f"Saved: {output_path}")
    else:
        print(mermaid)
"""



def main():
    if len(sys.argv) == 1:
        batch_mode()
    else:
        print("Kasutus: python generate_mermaid.py")
        print("  (batch mode - töötleb kõik loogilised mudelid)")


if __name__ == '__main__':
    main()