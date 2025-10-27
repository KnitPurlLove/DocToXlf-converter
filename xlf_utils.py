# xlf_utils.py
from lxml import etree
from docx import Document
import csv
import re
from copy import deepcopy
import difflib

XLIFF_NS = "urn:oasis:names:tc:xliff:document:1.2"

# ---------- normalization helpers ----------
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = s.replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def strip_html_like(text: str) -> str:
    if not text:
        return ''
    clean = re.sub(r'<[^>]+>', '', text)
    return normalize_text(clean)

def text_from_xml_element(elem):
    return normalize_text(''.join(elem.xpath('string()')))

# ---------- build mapping from CSV ----------
def build_mapping_from_csv(csv_path, src_col=0, tgt_col=1, encoding='utf-8'):
    mapping = {}
    with open(csv_path, newline='', encoding=encoding) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) <= max(src_col, tgt_col):
                continue
            src = normalize_text(row[src_col])
            tgt = row[tgt_col].strip()
            if src:
                mapping[src] = tgt
    return mapping

# ---------- build mapping from DOCX ----------
# DOCX tables: ignore column 1 (index 0), column2 -> src (index1), column3 -> tgt (index2)
def build_mapping_from_docx(docx_path, src_col_idx=1, tgt_col_idx=2):
    doc = Document(docx_path)
    mapping = {}
    for table in doc.tables:
        # try to iterate rows; if first row is header, it's okay — it will just be included if cells exist
        for row in table.rows:
            cells = row.cells
            if len(cells) <= max(src_col_idx, tgt_col_idx):
                continue
            src = strip_html_like(cells[src_col_idx].text)
            tgt = strip_html_like(cells[tgt_col_idx].text)
            if src:
                mapping[normalize_text(src)] = tgt
    return mapping

# ---------- helper to preserve tags ----------
def create_target_preserve_tags(src_elem, translated_text):
    """
    Copy source child element structure into new <target> element,
    then insert translated_text into the first suitable text node.
    """
    target_elem = etree.Element('{%s}target' % XLIFF_NS)
    target_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    children = list(src_elem)
    if not children:
        target_elem.text = translated_text
        return target_elem
    for child in children:
        target_elem.append(deepcopy(child))
    placed = False
    for el in target_elem.iter():
        if (el.text is None) or (not el.text.strip()):
            el.text = translated_text
            placed = True
            break
    if not placed:
        if target_elem.text:
            target_elem.text = target_elem.text + ' ' + translated_text
        else:
            target_elem.text = translated_text
    return target_elem

# ---------- main: apply mapping to XLF ----------
def apply_mapping_to_xlf(xlf_path, mapping, out_path,
                         preserve_tags=False, fuzzy=False, fuzzy_cutoff=0.85,
                         encoding='utf-8', preview=False):
    """
    mapping: dict(normalized_source_text -> target_text)
    preserve_tags: copy source tag structure into target (best-effort)
    fuzzy: use difflib.get_close_matches for near matches
    Returns (inserted_count, unmatched_list)
    """
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xlf_path, parser)
    root = tree.getroot()

    ns = root.nsmap.get(None) or XLIFF_NS
    nsmap_local = {'ns': ns}
    trans_units = root.xpath('//ns:trans-unit', namespaces=nsmap_local)
    if not trans_units:
        trans_units = root.findall('.//trans-unit')

    inserted = 0
    unmatched = []
    keys = list(mapping.keys())

    for tu in trans_units:
        src_elem = tu.find('{%s}source' % ns) or tu.find('source')
        if src_elem is None:
            continue
        src_text = text_from_xml_element(src_elem)
        key = normalize_text(src_text)
        tgt_text = None
        if key in mapping:
            tgt_text = mapping[key].strip()
        elif fuzzy and keys:
            best = difflib.get_close_matches(key, keys, n=1, cutoff=fuzzy_cutoff)
            if best:
                tgt_text = mapping[best[0]].strip()
        if tgt_text is not None:
            existing_target = tu.find('{%s}target' % ns) or tu.find('target')
            if existing_target is not None:
                tu.remove(existing_target)
            if preserve_tags:
                target_elem = create_target_preserve_tags(src_elem, tgt_text)
            else:
                target_elem = etree.Element('{%s}target' % ns)
                target_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                target_elem.text = tgt_text
            # insert after source if possible
            children = list(tu)
            try:
                src_index = children.index(src_elem)
                if src_index + 1 < len(children):
                    tu.insert(src_index + 1, target_elem)
                else:
                    tu.append(target_elem)
            except ValueError:
                tu.append(target_elem)
            inserted += 1
        else:
            unmatched.append(key)

    if preview:
        print(f"Inserted/updated {inserted} <target> elements.")
        print(f"Unmatched segments: {len(unmatched)} (showing first 15):")
        for u in unmatched[:15]:
            print('-', (u[:200] + '...') if len(u) > 200 else u)

    tree.write(out_path, xml_declaration=True, encoding=encoding, pretty_print=True)
    return inserted, unmatched
