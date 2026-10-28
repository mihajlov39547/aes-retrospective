"""Adapt the Facta sources to the shared SJEE template renderer and validator."""
from hashlib import sha256
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'sjee'))
import fill_sjee_template_docx as shared


def read_manuscript():
    sources = {}

    def read(name):
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f'Source outside manuscript: {name}')
        sources[name] = sha256(path.read_bytes()).hexdigest()
        return path.read_text(encoding='utf-8')

    wrapper = read('main.tex')
    contents = {name: read(name) for name in re.findall(r'\\input\{([^}]+)\}', wrapper)}
    meta = {n.macroname: shared.argument(n)
            for n in shared.parse(contents['content/metadata.tex'])
            if isinstance(n, shared.LatexMacroNode)}
    notes = [n for n in meta['author'] if isinstance(n, shared.LatexMacroNode)
             and n.macroname == 'thanks']
    if len(notes) != 1:
        raise ValueError('Expected one author affiliation footnote')
    references = []
    raw = contents['content/07_references.tex']
    entries = re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})', raw, re.S)
    for key, text in entries:
        references.append({'key': key, 'text': shared.plain(shared.parse(text))})
    if not references or len({r['key'] for r in references}) != len(references):
        raise ValueError('Missing or duplicate bibliography entries')
    data = {
        'title': shared.plain(meta['title']),
        'author': shared.plain([n for n in meta['author'] if n not in notes]),
        'affiliation': shared.plain(shared.argument(notes[0])),
        'abstract': shared.clean(shared.inline(shared.parse(contents['content/abstract.tex']))),
        'keywords': shared.clean(shared.inline(shared.parse(contents['content/keywords.tex']))),
        'blocks': [], 'references': references, 'source_sha256': sources,
        'subject': 'Facta Universitatis CPU AES manuscript draft',
        'source_comment': 'Generated from main.tex and content/*.tex; edit those sources.',
    }
    body = {name: text for name, text in contents.items() if name != 'content/07_references.tex'}
    for name, text in body.items():
        if re.match(r'content/\d', name):
            try:
                data['blocks'].extend(shared.blocks(text))
            except Exception as exc:
                raise ValueError(f'{name}: {exc}') from exc
    if not data['blocks']:
        raise ValueError('No manuscript body found')
    for block in data['blocks']:
        if block['kind'] == 'figure':
            path = (ROOT / block['image']).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError('Figure outside manuscript')
            sources[block['image']] = sha256(path.read_bytes()).hexdigest()
    # Manual bibitems define PDF citation numbers, even when first-citation order differs.
    shared.resolve_links(data, body, bibliography_order=True)
    return data


if __name__ == '__main__':
    shared.ROOT = ROOT
    shared.OUTPUT = ROOT / 'main_facta.docx'
    shared.BUILD = ROOT / 'build/docx'
    shared.read_manuscript = read_manuscript
    shared.main()
