r"""Regression checks for manuscript constructs added in October 2026.

Run: .\.venv-docx\Scripts\python.exe -m unittest discover -s tests
"""
import unittest
from docx.oxml.ns import qn
import fill_sjee_template_docx as g


class AdapterTests(unittest.TestCase):
    def test_numbered_list_keeps_all_paragraphs(self):
        result = g.blocks(r'\begin{enumerate}\item First.\item \textbf{Second.}\end{enumerate}')
        self.assertEqual([b['number'] for b in result], [1, 2])
        self.assertTrue(result[1]['runs'][0]['bold'])

    def test_widetilde_is_native_accent(self):
        node = g.omml(r'\frac{\widetilde{T}_{CPU}}{\widetilde{T}_{GPU}}')
        accents = list(node.iter(qn('m:acc')))
        self.assertEqual(len(accents), 2)
        self.assertTrue(all(a.find(qn('m:accPr')).find(qn('m:chr')).get(qn('m:val')) == '\u0303' for a in accents))

    def test_forward_reference_and_citation_order(self):
        source = r'\section{Test}See \ref{tab:later}, \cite{second,first}.\begin{table}\caption{Later}\label{tab:later}\end{table}'
        data = {'references': [{'key':'first'}, {'key':'second'}, {'key':'uncited'}],
                'runs': g.inline(g.parse(r'\ref{tab:later} \cite{second,first}'))}
        g.resolve_links(data, {'content/01_test.tex': source})
        self.assertEqual(data['citation_numbers'], {'second':1, 'first':2, 'uncited':3})
        self.assertEqual(''.join(r['text'] for r in data['runs']), '1 [1, 2]')

    def test_missing_reference_fails(self):
        data = {'references': [], 'runs': g.inline(g.parse(r'\ref{missing}'))}
        with self.assertRaisesRegex(ValueError, 'Unknown cross-reference'):
            g.resolve_links(data, {})

    def test_unknown_construct_fails(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            g.blocks(r'Important \unknown{content}')


if __name__ == '__main__':
    unittest.main()
