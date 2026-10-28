"""Build the Facta manuscript with the shared SJEE BibTeX/template workflow."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'sjee'))
import fill_sjee_template_docx as shared

read_shared_manuscript = shared.read_manuscript


def read_manuscript():
    data = read_shared_manuscript()
    data['subject'] = 'Facta Universitatis CPU AES manuscript draft'
    data['source_comment'] = (
        'Generated from main.tex, content/*.tex and references.bib; edit those sources.')
    return data


if __name__ == '__main__':
    shared.ROOT = ROOT
    shared.OUTPUT = ROOT / 'main_facta.docx'
    shared.BUILD = ROOT / 'build/docx'
    shared.read_manuscript = read_manuscript
    shared.main()
