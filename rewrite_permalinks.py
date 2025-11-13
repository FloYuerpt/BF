#!/usr/bin/env python3
"""
Rewrite the dfn-panel blocks in HTML files so that:
- The Permalink link points to the corresponding <dfn> id on the same filename (e.g. Overview.html#dfn-claims)
- If the original <dfn> has class "export" or data-export attribute, ensure a marker span with class "marker dfn-exported" is present
- Rebuild the "Referenced in:" <ul> by collecting all <a> elements in the document whose href starts with "#ref-for-{dfn-id}" and grouping them by their first-level list item in the current panels (approximate by looking for those refs elsewhere and linking)

This script modifies files in-place but creates a .bak backup first.

Usage: python3 rewrite_permalinks.py Overview.html
"""
import sys
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except Exception as e:
    print("BeautifulSoup (bs4) is required. Install with: pip install beautifulsoup4")
    raise


def process_file(p: Path):
    html = p.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # Map dfn id -> dfn tag
    dfn_map = {tag.get('id'): tag for tag in soup.find_all('dfn') if tag.get('id')}

    # Find all dfn-panel divs
    panels = soup.find_all('div', class_='dfn-panel')

    for panel in panels:
        # try to extract the dfn id from the panel id which is usually 'dfn-panel-for-dfn-<id-suffix>'
        pid = panel.get('id') or ''
        m = re.match(r'dfn-panel-for-(?:dfn-)?(.+)', pid)
        if not m:
            # fallback: try to read aria-label which contains the definition name
            # can't reliably map -> skip
            continue
        dfn_suffix = m.group(1)
        dfn_id = 'dfn-' + dfn_suffix if not dfn_suffix.startswith('dfn-') else dfn_suffix

        dfn_tag = dfn_map.get(dfn_id)
        # If not found, try alt name (without prefix)
        if dfn_tag is None:
            dfn_tag = dfn_map.get(dfn_suffix)

        # Update permalink href inside panel
        a = panel.find('a', class_='self-link')
        if a is None:
            # create one
            a = soup.new_tag('a', **{'class': 'self-link'})
            panel.div.insert(0, a)
        link = f"{p.name}#{dfn_id}" if dfn_id else f"#{dfn_suffix}"
        a['href'] = f"#{dfn_id}"
        a.string = 'Permalink'
        a['aria-label'] = f"Permalink for definition: {dfn_id}. Activate to close this dialog."

        # Ensure exported marker if dfn has export
        # Remove any existing marker of dfn-exported first to avoid duplicates
        existing_marker = panel.find('span', class_='marker dfn-exported')
        if dfn_tag is not None and ('export' in (dfn_tag.get('class') or []) or dfn_tag.has_attr('data-export')):
            if existing_marker is None:
                marker = soup.new_tag('span')
                marker['class'] = 'marker dfn-exported'
                marker['title'] = 'Definition can be referenced by other specifications'
                marker.string = 'exported'
                # append after the self-link
                if a.next_sibling:
                    a.insert_after(marker)
                else:
                    panel.div.append(marker)
        else:
            if existing_marker:
                existing_marker.decompose()

        # NOTE: previous versions attempted to rebuild the entire "Referenced in:" list
        # by scanning the whole document. That approach can mangle large documents
        # when parsed/serialized repeatedly. To avoid destructive edits, we do NOT
        # modify the existing "Referenced in:" <ul> here. This script only makes
        # two safe updates per panel:
        #  - ensure the permalink <a.self-link> points to the corresponding
        #    <dfn> id (href="#dfn-..."), and
        #  - add or remove the "exported" marker span based on the original
        #    <dfn> element having class "export" or a data-export attribute.
        #
        # If you still want the script to rebuild the "Referenced in:" lists,
        # please open an issue or modify the script to implement a custom,
        # non-destructive merging strategy.

    # backup original
    bak = p.with_suffix(p.suffix + '.bak')
    bak.write_text(html, encoding='utf-8')
    p.write_text(str(soup), encoding='utf-8')
    print(f"Processed {p} -> backup {bak}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: rewrite_permalinks.py file1.html [file2.html ...]')
        sys.exit(2)
    for f in sys.argv[1:]:
        process_file(Path(f))
