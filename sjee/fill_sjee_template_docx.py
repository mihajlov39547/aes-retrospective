"""Primary DOCX generator: copy SJEE styles, read shared sources, never use Pandoc.

The parser deliberately supports a bounded LaTeX subset and rejects unknown
constructs. build/docx/manuscript.json is a generated intermediate, not a source.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import re

import bibtexparser
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from latex2mathml.converter import convert as latex_mathml
from lxml import etree
from mathml2omml import convert as mathml_omml
from pylatexenc.latexwalker import (
    LatexWalker, get_default_latex_context_db, LatexCharsNode, LatexCommentNode,
    LatexMacroNode, LatexGroupNode, LatexMathNode, LatexSpecialsNode,
    LatexEnvironmentNode,
)
from pylatexenc.macrospec import MacroSpec

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'SJEE_Template.docx'
OUTPUT = ROOT / 'main_sjee.docx'
BUILD = ROOT / 'build' / 'docx'
TEMPLATE_HASH = '51ab1782847fabe6910f7fa4af264bc25c3bad8585f0db54d31fe963941e578d'
CONTEXT = get_default_latex_context_db()
CONTEXT.add_context_category('sjee', macros=[
    MacroSpec('thanks', '{'), MacroSpec('caption', '[{'),
    MacroSpec('multicolumn', '{{{'), MacroSpec('setlength', '{{'),
    MacroSpec('url', '{'), MacroSpec('href', '{{'),
], prepend=True)


def parse(text):
    return LatexWalker(text, latex_context=CONTEXT, tolerant_parsing=False).get_latex_nodes()[0]


def argument(node, index=-1):
    return node.nodeargd.argnlist[index].nodelist


def inline(nodes, **formatting):
    result = []
    for node in nodes:
        if isinstance(node, LatexCommentNode):
            continue
        if isinstance(node, LatexCharsNode):
            result.append(dict(text=re.sub(r'\s+', ' ', node.chars), **formatting))
        elif isinstance(node, LatexGroupNode):
            result.extend(inline(node.nodelist, **formatting))
        elif isinstance(node, LatexMathNode):
            raw = node.latex_verbatim()
            result.append(dict(math=raw[len(node.delimiters[0]):-len(node.delimiters[1])], **formatting))
        elif isinstance(node, LatexSpecialsNode):
            replacements = {'~': '\u00a0', '--': '\u2013', '---': '\u2014', "``": '\u201c', "''": '\u201d'}
            if node.specials_chars not in replacements:
                raise ValueError(f'Unsupported inline special: {node.latex_verbatim()}')
            result.append(dict(text=replacements[node.specials_chars], **formatting))
        elif isinstance(node, LatexMacroNode):
            name = node.macroname
            if name in ('emph', 'textit', 'textbf', 'texttt'):
                fmt = dict(formatting)
                fmt[{'emph': 'italic', 'textit': 'italic', 'textbf': 'bold', 'texttt': 'code'}[name]] = True
                result.extend(inline(argument(node), **fmt))
            elif name in ('url', 'href'):
                result.extend(inline(argument(node), **formatting))
            elif name in ('&', '_', '%', '#', '$', '{', '}', ',', ' ', '\\'):
                result.append(dict(text={',': '\u2009', ' ': ' ', '\\': '\n'}.get(name, name), **formatting))
            elif name == 'label':
                continue
            else:
                raise ValueError(f'Unsupported inline command: {node.latex_verbatim()}')
        else:
            raise ValueError(f'Unsupported inline content: {node.latex_verbatim()}')
    return result


def clean(runs):
    runs = deepcopy(runs)
    while runs and 'text' in runs[0] and not runs[0]['text'].strip():
        runs.pop(0)
    while runs and 'text' in runs[-1] and not runs[-1]['text'].strip():
        runs.pop()
    if runs and 'text' in runs[0]:
        runs[0]['text'] = runs[0]['text'].lstrip()
    if runs and 'text' in runs[-1]:
        runs[-1]['text'] = runs[-1]['text'].rstrip()
    return runs


def plain(nodes):
    runs = inline(nodes)
    if any('math' in r for r in runs):
        raise ValueError('Math in metadata/BibTeX text needs explicit handling')
    return ''.join(r['text'] for r in runs).strip()


def parse_table(node):
    caption = tabular = None
    for child in node.nodelist:
        if isinstance(child, (LatexCommentNode, LatexCharsNode)):
            if isinstance(child, LatexCharsNode) and child.chars.strip():
                raise ValueError('Unexpected text outside tabular')
        elif isinstance(child, LatexMacroNode):
            if child.macroname == 'caption':
                caption = clean(inline(argument(child)))
            elif child.macroname not in ('centering', 'small', 'setlength', 'label'):
                raise ValueError(f'Unsupported table command {child.macroname}')
        elif isinstance(child, LatexEnvironmentNode) and child.environmentname == 'tabular':
            tabular = child
        else:
            raise ValueError('Unsupported table content')
    if caption is None or tabular is None:
        raise ValueError('Each table needs a caption and a tabular')
    columns = plain(argument(tabular))
    if not re.fullmatch('[lcr]+', columns):
        raise ValueError(f'Unsupported column specification: {columns}')
    raw = ''.join(n.latex_verbatim() for n in tabular.nodelist)
    raw = re.sub(r'\\cmidrule(?:\([^)]*\))?\{[^}]*\}', '', raw)
    rows, cells, pending = [], [], []
    header_rows = None
    span = 1

    def finish_cell():
        nonlocal pending, span
        cells.append({'span': span, 'runs': clean(pending)})
        pending, span = [], 1

    for child in parse(raw):
        if isinstance(child, LatexSpecialsNode) and child.specials_chars == '&':
            finish_cell()
        elif isinstance(child, LatexMacroNode) and child.macroname == '\\':
            finish_cell()
            if sum(c['span'] for c in cells) != len(columns):
                raise ValueError('Table row width mismatch')
            rows.append(cells)
            cells = []
        elif isinstance(child, LatexMacroNode) and child.macroname in ('toprule', 'midrule', 'bottomrule'):
            if child.macroname == 'midrule' and header_rows is None:
                header_rows = len(rows)
        elif isinstance(child, LatexMacroNode) and child.macroname == 'multicolumn':
            if clean(pending):
                raise ValueError('Unsupported content before multicolumn')
            span = int(plain(argument(child, 0)))
            pending = inline(argument(child, 2))
        else:
            pending.extend(inline([child]))
    if clean(pending) or cells:
        raise ValueError('Table must end with a complete row')
    return {'kind': 'table', 'caption': caption, 'columns': columns,
            'rows': rows, 'header_rows': header_rows or 1}


def blocks(text):
    result, pending = [], []

    def flush():
        nonlocal pending
        runs = clean(pending)
        if runs:
            result.append({'kind': 'paragraph', 'runs': runs})
        pending = []

    for node in parse(text):
        if isinstance(node, LatexCharsNode):
            for i, chunk in enumerate(re.split(r'\n\s*\n', node.chars)):
                if i:
                    flush()
                pending.append({'text': re.sub(r'\s+', ' ', chunk)})
        elif isinstance(node, LatexMacroNode) and node.macroname in ('section', 'subsection'):
            flush()
            result.append({'kind': node.macroname, 'runs': clean(inline(argument(node)))})
        elif isinstance(node, LatexEnvironmentNode):
            flush()
            if node.environmentname == 'table':
                result.append(parse_table(node))
            elif node.environmentname == 'equation':
                raw = ''.join(n.latex_verbatim() for n in node.nodelist)
                result.append({'kind': 'equation', 'math': re.sub(r'\\label\{[^}]*\}', '', raw).strip()})
            else:
                raise ValueError(f'Unsupported environment {node.environmentname}; add explicit handling before export')
        else:
            pending.extend(inline([node]))
    flush()
    return result


def bibliography():
    database = bibtexparser.loads((ROOT / 'references.bib').read_text(encoding='utf-8'))
    references = []
    for entry in database.entries:
        def value(key):
            return plain(parse(entry.get(key, '')))
        names = []
        authors = entry.get('author', '')
        # Corporate authors protect "and" inside braces (e.g. NIST).
        boundaries = [m for m in re.finditer(r'\s+and\s+', authors)
                      if authors[:m.start()].count('{') == authors[:m.start()].count('}')]
        people, start = [], 0
        for match in boundaries:
            people.append(authors[start:match.start()])
            start = match.end()
        people.append(authors[start:])
        for person in people:
            if person.startswith('{') or ',' not in person:
                names.append(plain(parse(person)))
            else:
                last, first = person.split(',', 1)
                names.append(' '.join(word[0] + '.' for word in first.split()) + ' ' + last)
        fields = [', '.join(names) + ': ' + value('title')]
        for key in ('journal', 'booktitle', 'institution', 'publisher', 'howpublished'):
            if value(key):
                fields.append(value(key))
        if value('type'):
            fields.append(value('type') + (' ' + value('number') if value('number') else ''))
        else:
            for key, prefix in [('volume', 'Vol. '), ('number', 'No. ')]:
                if value(key):
                    fields.append(prefix + value(key))
        for key, prefix in [('year', ''), ('pages', 'pp. '), ('doi', 'doi: '), ('url', ''), ('note', '')]:
            if value(key):
                fields.append(prefix + value(key))
        references.append({'key': entry['ID'], 'text': ', '.join(fields) + '.'})
    if not references:
        raise ValueError('No bibliography entries parsed')
    return references


def read_manuscript():
    wrapper = re.sub(r'(?m)^%.*$', '', (ROOT / 'main.tex').read_text(encoding='utf-8'))
    inputs = re.findall(r'\\input\{([^}]+)\}', wrapper)
    contents = {name: (ROOT / name).read_text(encoding='utf-8') for name in inputs}
    meta = {n.macroname: argument(n) for n in parse(contents['content/metadata.tex']) if isinstance(n, LatexMacroNode)}
    notes = [n for n in meta['author'] if isinstance(n, LatexMacroNode) and n.macroname == 'thanks']
    if len(notes) != 1:
        raise ValueError('This template adapter expects one author affiliation footnote')
    data = {'title': plain(meta['title']),
            'author': plain([n for n in meta['author'] if n not in notes]),
            'affiliation': plain(argument(notes[0])),
            'abstract': clean(inline(parse(contents['content/abstract.tex']))),
            'keywords': clean(inline(parse(contents['content/keywords.tex']))),
            'blocks': [], 'references': bibliography(),
            'source_sha256': {name: sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in inputs + ['main.tex', 'references.bib']}}
    for name, text in contents.items():
        if re.match(r'content/\d', name):
            try:
                data['blocks'].extend(blocks(text))
            except Exception as exc:
                raise ValueError(f'{name}: {exc}') from exc
    if not data['blocks']:
        raise ValueError('No manuscript body found')
    return data


def omml(tex):
    xml = mathml_omml(latex_mathml(tex))
    root = etree.fromstring(('<root xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">' + xml + '</root>').encode('utf-8'))
    return root[0]


def write_runs(paragraph, runs, warnings):
    for item in runs:
        if 'math' in item:
            try:
                paragraph._p.append(omml(item['math']))
            except Exception as exc:
                paragraph.add_run('[MATH CLEANUP: ' + item['math'] + ']')
                warnings.append(f"Manual math conversion needed: {item['math']} ({exc})")
        else:
            run = paragraph.add_run(item['text'])
            if item.get('bold'):
                run.bold = True
            if item.get('italic'):
                run.italic = True
            if item.get('code'):
                run.font.name = 'Courier New'


def fill_footnote(document, text):
    part = next(p for p in document.part.package.parts if str(p.partname) == '/word/footnotes.xml')
    root = parse_xml(part.blob)
    for note in list(root):
        if note.get(qn('w:id')) == '2':
            root.remove(note)
        elif note.get(qn('w:id')) == '1':
            node = note.find(qn('w:p'))
            marker = deepcopy(node.find('.//' + qn('w:footnoteRef')).getparent())
            paragraph = Paragraph(node, document._body)
            paragraph.clear()
            node.append(marker)
            paragraph.add_run(' ' + text)
    part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def render(data, temporary):
    copyfile(SOURCE, temporary)
    document = Document(temporary)
    prototypes = {}
    for p in document.paragraphs:
        prototypes.setdefault(p.style.style_id, deepcopy(p._p))
    marker = deepcopy(prototypes['JAuthor'].find('.//' + qn('w:footnoteReference')).getparent())
    table_properties = deepcopy(document.tables[0]._tbl.tblPr)
    body = document._element.body
    for node in list(body):
        if node.tag != qn('w:sectPr'):
            body.remove(node)
    warnings = []

    def paragraph(style, runs=None):
        node = deepcopy(prototypes[style])
        p = Paragraph(node, document._body)
        p.clear()
        body.insert(len(body) - 1, node)
        if runs:
            write_runs(p, runs, warnings)
        return p

    paragraph('JTitle', [{'text': data['title']}])
    paragraph('JAuthor', [{'text': data['author']}])._p.append(marker)
    paragraph('JAbstract', [{'text': 'Abstract: ', 'bold': True}] + data['abstract'])
    paragraph('JAbstract', [{'text': 'Keywords: ', 'bold': True}] + data['keywords'])
    fill_footnote(document, data['affiliation'])
    for part in document.part.package.parts:
        if str(part.partname).startswith('/word/header') and str(part.partname).endswith('.xml'):
            for node in part.element.findall('.//' + qn('w:p')):
                Paragraph(node, document._body).clear()
    section = subsection = table_number = equation = 0
    after_equation = False
    for block in data['blocks']:
        kind = block['kind']
        if kind == 'section':
            section += 1
            subsection = 0
            paragraph('JSubtitle', [{'text': f'{section}\t'}] + block['runs'])
        elif kind == 'subsection':
            subsection += 1
            paragraph('JSubSubTitle', [{'text': f'{section}.{subsection}\t'}] + block['runs'])
        elif kind == 'paragraph':
            paragraph('JText-noIndent' if after_equation else 'JText', block['runs'])
        elif kind == 'equation':
            equation += 1
            p = paragraph('JEquation')
            p.add_run('\t')
            write_runs(p, [{'math': block['math']}], warnings)
            p.add_run(f'\t({equation})')
        elif kind == 'table':
            table_number += 1
            p = paragraph('JFigure', [{'text': f'Table {table_number}', 'bold': True}, {'text': '\n'}] +
                          [dict(r, italic=True) for r in block['caption']])
            p.paragraph_format.keep_with_next = True
            ncols = len(block['columns'])
            table = document.add_table(rows=len(block['rows']), cols=ncols)
            props = deepcopy(table_properties)
            # Original tblStyle points at a paragraph style; retain explicit
            # template grid borders/alignment, not that invalid style reference.
            old_style = props.find(qn('w:tblStyle'))
            if old_style is not None:
                props.remove(old_style)
            props.find(qn('w:tblW')).set(qn('w:w'), '7088')
            table._tbl.replace(table._tbl.tblPr, props)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            weights = [5.0] * ncols
            for row in block['rows']:
                col = 0
                for cell in row:
                    length = len(''.join(r.get('text', r.get('math', '')) for r in cell['runs']))
                    if cell['span'] == 1:
                        weights[col] = max(weights[col], min(length, 23) + 2)
                    col += cell['span']
            widths = [Cm(12.5 * w / sum(weights)) for w in weights]
            for i, column in enumerate(table.columns):
                column.width = widths[i]
            for ri, row in enumerate(block['rows']):
                word_row = table.rows[ri]
                trpr = word_row._tr.get_or_add_trPr()
                trpr.append(OxmlElement('w:cantSplit'))
                if ri < block['header_rows']:
                    trpr.append(OxmlElement('w:tblHeader'))
                for i, cell in enumerate(word_row.cells):
                    cell.width = widths[i]
                col = 0
                for cell in row:
                    target = word_row.cells[col]
                    if cell['span'] > 1:
                        target = target.merge(word_row.cells[col + cell['span'] - 1])
                    target.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    p = target.paragraphs[0]
                    p.style = document.styles['JTableText']
                    p.paragraph_format.keep_with_next = ri < block['header_rows']
                    write_runs(p, cell['runs'], warnings)
                    col += cell['span']
        else:
            raise ValueError(f'Unhandled block kind {kind}')
        after_equation = kind == 'equation'
    paragraph('JSubtitle', [{'text': 'References'}])
    for reference in data['references']:
        paragraph('JReference', [{'text': reference['text']}])
    document.core_properties.title = data['title']
    document.core_properties.author = data['author']
    document.core_properties.subject = 'SJEE manuscript draft'
    document.core_properties.comments = 'Generated from content/*.tex and references.bib; edit those sources.'
    used = {v for el in body.iter() for k, v in el.attrib.items() if k.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}')}
    for rid, rel in list(document.part.rels.items()):
        if rid not in used and rel.reltype.rsplit('/', 1)[-1] in ('image', 'oleObject'):
            document.part.drop_rel(rid)
    document.save(temporary)
    return warnings


def validate(path, data):
    with ZipFile(SOURCE) as source, ZipFile(path) as result:
        for name in ['word/styles.xml', 'word/numbering.xml']:
            if etree.tostring(parse_xml(source.read(name)), method='c14n') != etree.tostring(parse_xml(result.read(name)), method='c14n'):
                raise ValueError(f'Template styles/numbering changed: {name}')
        src = parse_xml(source.read('word/document.xml'))
        out = parse_xml(result.read('word/document.xml'))
        for tag in ('pgSz', 'pgMar', 'cols'):
            if src.find('.//' + qn('w:' + tag)).attrib != out.find('.//' + qn('w:' + tag)).attrib:
                raise ValueError(f'Page setting changed: {tag}')
        if len(out.findall('.//' + qn('w:tbl'))) != sum(b['kind'] == 'table' for b in data['blocks']):
            raise ValueError('Table count mismatch')
        for name in result.namelist():
            if name.startswith('word/header') and name.endswith('.xml'):
                if ''.join(parse_xml(result.read(name)).itertext()).strip():
                    raise ValueError(f'Sample header text remains: {name}')
        if out.findall('.//' + qn('w:object')):
            raise ValueError('Legacy template equation objects remain')


def main():
    if sha256(SOURCE.read_bytes()).hexdigest() != TEMPLATE_HASH:
        raise ValueError('Source template changed; inspect and adapt the template mapping first')
    if OUTPUT.is_symlink() or (OUTPUT.exists() and SOURCE.samefile(OUTPUT)):
        raise ValueError('Output must not link to the original template')
    data = read_manuscript()
    BUILD.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='sjee-docx-', dir=BUILD) as directory:
        temporary = Path(directory) / 'main_sjee.docx'
        warnings = render(data, temporary)
        validate(temporary, data)
        for name, digest in data['source_sha256'].items():
            if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Source changed during generation: {name}; rerun')
        if sha256(SOURCE.read_bytes()).hexdigest() != TEMPLATE_HASH:
            raise ValueError('Original template hash changed')
        temporary.replace(OUTPUT)
    (BUILD / 'manuscript.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'output': str(OUTPUT), 'generator': 'SJEE template copy; no Pandoc',
              'template_sha256': TEMPLATE_HASH, 'source_sha256': data['source_sha256'],
              'tables': sum(b['kind'] == 'table' for b in data['blocks']),
              'equations': sum(b['kind'] == 'equation' for b in data['blocks']),
              'references': len(data['references']), 'warnings': warnings,
              'manual_review': ['Connect unchanged typed author-year mentions to numeric references.',
                                'Review equation appearance, table pagination and reference punctuation in Word.',
                                'Discussion and Acknowledgments retain source placeholders.',
                                'Caption/equation numbers are generated literals, not Word cross-reference fields.']}
    (BUILD / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Created {OUTPUT}: {report["tables"]} tables, {report["equations"]} display equation(s), {report["references"]} references.')
    for warning in warnings:
        print('WARNING:', warning)
    print('Preserved SJEE styles/page settings. Cleared sample headers. Original template unchanged.')
    print('Source: content/*.tex and references.bib. Report: build/docx/build_report.json')


if __name__ == '__main__':
    main()
