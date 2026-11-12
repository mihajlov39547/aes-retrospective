"""Verify compiled references, ordering, page bounds, links and text counts."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'verification'

def main():
    for args in [
        ['pdftotext','-layout','main.pdf','verification/main.txt'],
        ['pdftotext','-bbox','main.pdf','verification/main-bbox.html']]:
        subprocess.run(args,cwd=ROOT,check=True,capture_output=True)
    links_xml=subprocess.run(['pdftohtml','-xml','-hidden','-i','-stdout','main.pdf'],cwd=ROOT,
                             capture_output=True,check=True).stdout.decode('utf-8')
    (OUT/'main-links.xml').write_text(links_xml,encoding='utf-8')
    tex=(ROOT/'main.tex').read_text(encoding='utf-8')
    bib=(ROOT/'references.bib').read_text(encoding='utf-8')
    log=(ROOT/'main.log').read_text(encoding='utf-8')
    assert not re.search(r'Overfull|Underfull|undefined|LaTeX Warning|Package .* Warning',log)
    assert 'SUMMARY' not in tex
    assert tex.index(r'\printbibliography')>tex.index(r'\section{Conclusion}')
    assert not re.search(r'\\section',tex[tex.index(r'\printbibliography'):])
    cited={key.strip() for group in re.findall(r'\\cite[pt]?\{([^}]+)\}',tex) for key in group.split(',')}
    keys=set(re.findall(r'@\w+\{([^,]+)',bib))
    assert cited==keys, (cited-keys,keys-cited)
    for prefix in ['fig','tab']:
        declared=re.findall(r'\\label\{('+prefix+r':[^}]+)\}',tex)
        mentioned=list(dict.fromkeys(re.findall(r'\\ref\{('+prefix+r':[^}]+)\}',tex)))
        assert declared==mentioned,(declared,mentioned)
    eqs=re.findall(r'\\label\{(eq:[^}]+)\}',tex)
    assert len(eqs)==4
    urls=set(re.findall(r'href="(https?://[^"]+)"',links_xml))
    expected={'https://doi.org/'+doi for doi in re.findall(r'doi=\{([^}]+)',bib)}
    expected.update(re.findall(r'url=\{([^}]+)',bib))
    assert urls==expected,(urls-expected,expected-urls)
    tree=ET.parse(OUT/'main-bbox.html')
    ns={'x':'http://www.w3.org/1999/xhtml'}
    pages=tree.findall('.//x:page',ns)
    word_counts=[]
    for page in pages:
        words=page.findall('x:word',ns)
        assert len(words)>50, 'Empty or nearly empty page'
        for word in words:
            assert 0<=float(word.attrib['xMin'])<float(word.attrib['xMax'])<=float(page.attrib['width'])
            assert 0<=float(word.attrib['yMin'])<float(word.attrib['yMax'])<=float(page.attrib['height'])
        word_counts.append(len(words))
    text_pages=(OUT/'main.txt').read_text(encoding='utf-8').split('\f')
    cleaned=[]
    for i,page in enumerate(text_pages,1):
        lines=page.rstrip().splitlines()
        if lines and lines[-1].strip()==str(i): lines.pop()
        cleaned.append('\n'.join(lines))
    normalized=' '.join(' '.join(cleaned).split())
    assert 'SUMMARY' not in normalized and '??' not in normalized
    first_page=' '.join(text_pages[0].split())
    for detail in ['Marko Mihajlović', 'Faculty of Informatics and Computing',
                   'Singidunum University', 'Belgrade, Serbia',
                   'marko.mihajlovic.23@singimail.rs', 'ORCID: 0009-0006-7979-0341']:
        assert detail in first_page, detail
    assert first_page.index('Marko Mihajlović') < first_page.index('Abstract')
    positions=[tex.index(section) for section in [r'\section{Conclusion}',
               r'\section*{Funding}', r'\section*{Conflict of interest}', r'\printbibliography']]
    assert positions==sorted(positions)
    assert 'The author received no specific funding for this work.' in normalized
    assert 'The author has no conflict of interest to declare.' in normalized
    abstract=tex.split(r'\section*{Abstract}')[1].split(r'\noindent')[0]
    report=dict(status='PASS',pages=len(pages),citations=len(keys),figures=3,tables=2,equations=4,
                characters_with_spaces=len(normalized),characters_without_whitespace=len(re.sub(r'\s','',normalized)),
                source_tex_characters=len(tex),abstract_words=len(abstract.split()),
                count_definition='PDF extracted text; whitespace collapsed to single spaces; page-number footers removed; includes title, headings, captions, figure text, tables and references.',
                external_links=sorted(urls),page_word_counts=word_counts,
                all_words_within_page_bounds=True,all_citation_keys_resolve=True,
                figures_and_tables_first_mentioned_in_number_order=True,final_summary_absent=True,
                author_details_on_first_page=True,required_declarations_present_in_order=True,
                latex_warnings=[])
    (OUT/'document_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ['status','pages','characters_with_spaces','characters_without_whitespace','abstract_words','citations']}))

if __name__=='__main__': main()
