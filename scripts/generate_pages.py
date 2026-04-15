#!/usr/bin/env python3

import json
import glob
import re
from pathlib import Path

#Sisend teekonnad
INPUT_DIR = "fsh-generated/resources"
PAGECONTENT_DIR = "input/pagecontent"
INCLUDES_DIR = "input/includes"
SUSHI_CONFIG = "sushi-config.yaml"


def scan_logical_models():
    models = []
    files = sorted(glob.glob(f"{INPUT_DIR}/StructureDefinition-*.json"))

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            sd = json.load(f)

        if (sd.get('resourceType') != 'StructureDefinition'
                or sd.get('kind') != 'logical'):
            continue

        model_id = sd.get('id', '')
        models.append({
            'id': model_id,                           
            'title': sd.get('title', sd.get('name', model_id)),
            'description': sd.get('description', ''),
            'page_file': f'model-{model_id.lower()}.xml',   
            'page_url': f'model-{model_id.lower()}.html',   
        })

    return models


def update_sushi_config(models):
    config_path = Path(SUSHI_CONFIG)
    if not config_path.exists():
        print("  ERROR: sushi-config.yaml not found!")
        return False

    content = config_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    pages_start = None
    pages_end = None

    for i, line in enumerate(lines):
        if pages_start is None:
            if re.match(r'^pages\s*:', line):
                pages_start = i
                continue
        if pages_start is not None and pages_end is None:
            if line and not line[0].isspace() and not line.startswith('#'):
                pages_end = i
                break

    if pages_start is None:
        pages_start = len(lines)
        pages_end = len(lines)
    elif pages_end is None:
        pages_end = len(lines)


    new_pages = ['pages:']
    new_pages.append('  index.md:')
    new_pages.append('    title: Avaleht')
    new_pages.append('  infomudelid.md:')
    new_pages.append('    title: Infomudelid')
    for m in models:
        new_pages.append(f'    {m["page_file"]}:')    
        new_pages.append(f'      title: {m["title"]}')

    new_lines = lines[:pages_start] + new_pages + lines[pages_end:]


    final_content = '\n'.join(new_lines)
    final_content = re.sub(
        r'^menu\s*:.*?(?=\n[a-zA-Z]|\Z)',
        '',
        final_content,
        count=1,
        flags=re.MULTILINE | re.DOTALL
    )
    final_content = re.sub(r'\n{3,}', '\n\n', final_content)

    config_path.write_text(final_content, encoding='utf-8')
    print(f"  Config: {SUSHI_CONFIG} updated")
    return True


def generate_model_page(model):
    model_id = model['id']
    title = model['title']
    desc = model['description'] or title

   
    xml = f'''<div xmlns="http://www.w3.org/1999/xhtml">

  <h3>{title}</h3>

  <p>{desc}</p>

  <p>
    <a href="infomudelid.html">\u2190 Tagasi infomudelite nimekirja</a> |
    <a href="StructureDefinition-{model_id}.html">FHIR StructureDefinition</a>
  </p>

  <h4>Klassidiagramm</h4>

  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js">//</script>
  <script>
  //
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  //
  </script>

  {{% include generated-mermaid-{model_id}.xhtml %}}

  <h4>Andmeelemendid</h4>

  {{% include generated-table-{model_id}.xhtml %}}

</div>'''

    return xml


def generate_overview_page(models):
    rows = []
    for m in models:
        rows.append(
            f'| [{m["title"]}]({m["page_url"]}) '
            f'| {m["description"]} '
            f'| [StructureDefinition](StructureDefinition-{m["id"]}.html) |'
        )

    table_rows = '\n'.join(rows)

    md = f'''### Infomudelid

K\u00f5ik defineeritud infomudelid.

| Infomudel | Kirjeldus | FHIR definitsioon |
|---|---|---|
{table_rows}
'''
    return md


def generate_menu_xml(models):
    model_items = []
    for m in models:
        model_items.append(
            f'      <li><a href="{m["page_url"]}">{m["title"]}</a></li>'
        )

    items_str = '\n'.join(model_items)

    xml = f'''<ul xmlns="http://www.w3.org/1999/xhtml" class="nav navbar-nav">
  <li><a href="index.html">Avaleht</a></li>
  <li class="dropdown">
    <a data-toggle="dropdown" href="#" class="dropdown-toggle">Infomudelid<b class="caret"> </b></a>
    <ul class="dropdown-menu">
      <li><a href="infomudelid.html">K\u00f5ik infomudelid</a></li>
      <li role="separator" class="divider"> </li>
{items_str}
    </ul>
  </li>
  <li><a href="artifacts.html">Artefaktid</a></li>
</ul>'''

    return xml


def cleanup_old_pages(models):
    valid_pages = {m['page_file'] for m in models}
    pagecontent = Path(PAGECONTENT_DIR)

    if not pagecontent.exists():
        return

    for f in pagecontent.iterdir():
        if f.name.startswith('model-') and f.suffix == '.xml':
            if f.name.lower() not in {p.lower() for p in valid_pages}:
                f.unlink()
                print(f"  Removed old page: {f.name}")
            elif f.name not in valid_pages:
                correct_name = next(p for p in valid_pages if p.lower() == f.name.lower())
                new_path = f.parent / correct_name
                f.rename(new_path)
                print(f"  Renamed: {f.name} -> {correct_name}")


def main():
    print("=== Auto-generating IG pages ===\n")

    models = scan_logical_models()
    print(f"Found {len(models)} logical model(s):")
    for m in models:
        print(f"  - {m['id']} -> {m['page_file']}")
    print()

    if not models:
        print("No logical models found")
        return

    Path(PAGECONTENT_DIR).mkdir(parents=True, exist_ok=True)
    Path(INCLUDES_DIR).mkdir(parents=True, exist_ok=True)

    print("Updating config...")
    update_sushi_config(models)

    cleanup_old_pages(models)

    print("\nGenerating pages...")
    for m in models:
        page_path = Path(PAGECONTENT_DIR) / m['page_file']   
        page_content = generate_model_page(m)
        page_path.write_text(page_content, encoding='utf-8')
        print(f"  Page:     {page_path}")

    overview_path = Path(PAGECONTENT_DIR) / 'infomudelid.md'
    overview_content = generate_overview_page(models)
    overview_path.write_text(overview_content, encoding='utf-8')
    print(f"  Overview: {overview_path}")

    menu_path = Path(INCLUDES_DIR) / 'menu.xml'
    menu_content = generate_menu_xml(models)
    menu_path.write_text(menu_content, encoding='utf-8')
    print(f"  Menu:     {menu_path}")

    print(f"\n=== Done: {len(models)} model(s) configured ===")


if __name__ == '__main__':
    main()