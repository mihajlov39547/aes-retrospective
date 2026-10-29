"""Convert the two UTF-8 LaTeX sources using Pandoc and existing journal styles.

The source .tex files remain the single source of manuscript content. SJEE
styles are adapted to the local author instructions by docx_layout.py.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from docx_layout import format_docx

ROOT = Path(__file__).resolve().parent
STEMS = {'article': 'mihajlovic2026validiran', 'cover': 'naslovna_mihajlovic2026validiran'}
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}


def nodes(value):
    if isinstance(value, dict):
        if 't' in value:
            yield value
        for item in value.values():
            yield from nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def pandoc(arguments, log):
    result = subprocess.run(['pandoc', *map(str, arguments)], cwd=ROOT,
                            capture_output=True, encoding='utf-8')
    log.write_text(result.stderr, encoding='utf-8')
    if result.returncode or result.stderr.strip():
        raise RuntimeError(f'Pandoc reported an error or warning; inspect {log}')


def clean_template(source, destination):
    # Reuse styles without showing another journal's header/footer content.
    # Work on a copy; the existing SJEE/Facta templates are never modified.
    with ZipFile(source) as src, ZipFile(destination, 'w') as dst:
        for entry in src.infolist():
            data = src.read(entry.filename)
            if entry.filename == 'word/document.xml':
                tree = ET.fromstring(data)
                for section in tree.findall('.//w:sectPr', NS):
                    for tag in ('headerReference', 'footerReference'):
                        for child in section.findall(f'w:{tag}', NS):
                            section.remove(child)
                data = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
            dst.writestr(entry, data)


def build(kind, reference, build_dir):
    stem = STEMS[kind]
    source = ROOT / f'{stem}.tex'
    text = source.read_text(encoding='utf-8')
    # Strip font selection in a generated copy: Pandoc consumes a following
    # numeric year after \selectfont. Word uses the reference document's fonts.
    prepared = re.sub(r'\\fontsize\s*\{[^{}]*\}\s*\{[^{}]*\}', '', text)
    prepared = re.sub(r'\\selectfont\b', '', prepared)
    # Pandoc leaks booktabs trim/range arguments into the first header cell.
    # Word table borders are applied by docx_layout instead.
    prepared = re.sub(r'\\cmidrule(?:\[[^\]]*\])?(?:\([^)]*\))?\{[^{}]*\}', '', prepared)
    equation_labels = {}
    for number, equation in enumerate(re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}', text, re.S), 1):
        for label in re.findall(r'\\label\{([^{}]+)\}', equation):
            equation_labels[label] = number
    prepared = re.sub(r'\\eqref\{([^{}]+)\}',
                      lambda m: f'({equation_labels[m[1]]})', prepared)
    prepared = re.sub(r'width=(\d*\.?\d*)\\linewidth',
                      lambda m: f'width={12.6 * float(m[1] or 1):g}cm', prepared)
    # Word cannot embed PDF figures. Rasterize a build-only copy at print resolution.
    figures = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}', text)
    for figure in dict.fromkeys(figures):
        if Path(figure).suffix.lower() != '.pdf':
            continue
        if not shutil.which('pdftocairo'):
            raise RuntimeError('pdftocairo is required to convert PDF figures for DOCX')
        target = build_dir / Path(figure).stem
        subprocess.run(['pdftocairo', '-png', '-singlefile', '-r', '300',
                        str(ROOT / figure), str(target)], check=True, capture_output=True)
        prepared = prepared.replace('{' + figure + '}', '{' + target.with_suffix('.png').as_posix() + '}')
    intermediate = build_dir / f'{stem}.tex'
    intermediate.write_text(prepared, encoding='utf-8')
    ast_path = build_dir / f'{stem}.json'
    bib_options = ['--citeproc', '--bibliography', ROOT / 'references.bib',
                   '--metadata=reference-section-title:Literatura'] if '\\addbibresource' in text else []
    pandoc([intermediate, '--from=latex', '--to=json', *bib_options, '-o', ast_path],
           build_dir / f'{stem}-read.log')
    ast = json.loads(ast_path.read_text(encoding='utf-8'))
    if bib_options:
        # Citeproc appends references; preserve the manuscript's bibliography-before-summary order.
        blocks = ast['blocks']
        refs = [b for b in blocks if b['t'] == 'Div' and b['c'][0][0] == 'refs']
        headings = [b for b in blocks if b['t'] == 'Header' and
                    any(n.get('t') == 'Str' and n.get('c') == 'Literatura' for n in nodes(b))]
        blocks[:] = [b for b in blocks if b not in refs + headings]
        summary_index = next(i for i, b in enumerate(blocks) if b['t'] == 'Header' and
                             any(n.get('t') == 'Str' and n.get('c') == 'SUMMARY' for n in nodes(b)))
        blocks[summary_index:summary_index] = headings + refs
        ast_path.write_text(json.dumps(ast, ensure_ascii=False), encoding='utf-8')
    all_nodes = list(nodes(ast))
    counts = Counter(n['t'] for n in all_nodes)
    if counts['RawBlock'] or counts['RawInline']:
        raise ValueError(f'{stem}: unconverted LaTeX in Pandoc AST; inspect {ast_path}')
    expected_tables = len(re.findall(r'\\begin\{table\}', text))
    expected_equations = len(re.findall(r'\\begin\{equation\}', text))
    if bib_options:
        cited = {key.strip() for keys in re.findall(r'\\(?:citep|citet|cite|parencite|textcite)(?:\[[^\]]*\])*\{([^{}]+)\}', text)
                 for key in keys.split(',')}
        reference_ids = {n['c'][0][0][4:] for n in all_nodes
                         if n['t'] == 'Div' and n['c'][0][0].startswith('ref-')}
        if reference_ids != cited:
            raise ValueError(f'Bibliography mismatch: cited {cited}, rendered {reference_ids}')
        expected_references = len(cited)
        references = len(reference_ids)
    else:
        expected_references = len(re.findall(r'\\item\b', text))
        references = sum(len(n['c'][1]) for n in all_nodes if n['t'] == 'OrderedList')
    if counts['Table'] != expected_tables or references != expected_references:
        raise ValueError(f'{stem}: table or reference content was lost during conversion')
    temporary = build_dir / f'{stem}.docx'
    pandoc([ast_path, '--from=json', '--to=docx', '--standalone', '--number-sections',
            '--metadata=lang:sr-Latn', '--reference-doc', reference, '-o', temporary],
           build_dir / f'{stem}-write.log')
    layout_report = format_docx(temporary, kind)
    with ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f'Invalid DOCX archive member: {bad}')
        tree = ET.fromstring(archive.read('word/document.xml'))
    tables = len(tree.findall('.//w:tbl', NS))
    equations = len(tree.findall('.//m:oMathPara', NS))
    images = len(tree.findall('.//w:drawing', NS))
    if images != len(figures):
        raise ValueError(f'{stem}: DOCX figure count does not match the source')
    if tables != expected_tables or equations != expected_equations:
        raise ValueError(f'{stem}: DOCX table/equation count does not match the source')
    visible = ''.join(tree.itertext())
    if re.search(r'\[eq:[^\]]+\]', visible):
        raise ValueError('Unresolved equation reference in DOCX')
    if kind == 'cover':
        for required in ('2026', '0009-0006-7979-0341', 'marko.mihajlovic.23@singimail.rs'):
            if required not in visible:
                raise ValueError(f'Cover lost required content: {required}')
    elif not all(heading in visible for heading in ('Apstrakt', 'Abstract', 'LITERATURA', 'SUMMARY')):
        raise ValueError('Article lost an abstract, references or summary heading')
    output = ROOT / f'{stem}.docx'
    shutil.copyfile(temporary, output)
    print(f'Built {output} ({tables} tables, {equations} display equations, {references} references)')
    return dict(source=str(source), source_sha256=sha256(source.read_bytes()).hexdigest(),
                output=str(output), tables=tables, equations=equations, references=references, figures=images,
                layout=layout_report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', choices=['all', *STEMS], default='all')
    parser.add_argument('--reference-doc', type=Path, default=ROOT.parent / 'sjee/SJEE_Template.docx')
    args = parser.parse_args()
    if not shutil.which('pandoc'):
        parser.error('Pandoc is required on PATH')
    template = args.reference_doc.resolve()
    if not template.is_file():
        parser.error(f'Reference template does not exist: {template}')
    build_dir = ROOT / 'build/docx'
    build_dir.mkdir(parents=True, exist_ok=True)
    reference = build_dir / 'reference.docx'
    clean_template(template, reference)
    reports = [build(kind, reference, build_dir) for kind in
               (STEMS if args.document == 'all' else [args.document])]
    (build_dir / 'build_report.json').write_text(json.dumps(
        dict(template=str(template), documents=reports, warnings=[]), ensure_ascii=False, indent=2),
        encoding='utf-8')


if __name__ == '__main__':
    main()
