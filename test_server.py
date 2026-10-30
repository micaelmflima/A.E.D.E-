import unittest
from io import BytesIO
from email.message import Message
from openpyxl import Workbook
import server

def workbook(rows):
    book = Workbook(); sheet = book.active; sheet.title = 'Alunos_Modelo'
    sheet.append(['Aluno_ID','Nome','Turma','Presença_1tri','Media_1tri','Presença_2tri','Media_2tri'])
    for row in rows: sheet.append(row)
    result = BytesIO(); book.save(result); return result.getvalue()

class AnalysisTests(unittest.TestCase):
    def test_score_range_and_order(self):
        content = workbook([['a','Ana','A',.95,8,.9,7],['b','Bia','A',.5,5,.4,4]])
        for period in (1, 2):
            result = server.analyze(content, period)
            self.assertEqual(result['total'], 2)
            self.assertTrue(all  (0 <= r['score'] <= 100 for r in result['students']))
            self.assertEqual(result['students'], sorted(result['students'], key=lambda r: (-r['score'], r['name'])))

    def test_scores_and_missing_period(self):
        content = workbook([['a','Ana','A',.95,8,.9,7],['b','Bia','A',.5,5,.4,4],['c','Caio','A',.9,7,.8,6],['d','Dora','B',.9,7,None,None]])
        result = server.analyze(content, 2)
        self.assertEqual(result['skipped'], 1)
        by_id = {r['id']:r for r in result['students']}
        self.assertGreater(by_id['b']['score'], by_id['a']['score'])
        self.assertIsNotNone(by_id['a']['context'])
        self.assertAlmostEqual(by_id['a']['score'], .8 * by_id['a']['model'] + .2 * by_id['a']['context'], delta=.11)
        self.assertIsNone(server.analyze(content, 1)['students'][0]['context'])

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError): server.analyze(b'bad', 1)
        with self.assertRaises(ValueError): server.analyze(workbook([['x','A','T',.8,7,None,None],['x','B','T',.8,7,None,None]]), 1)
        pending = server.analyze(workbook([['x','A','T',.8,7,None,None]]), 2)
        self.assertEqual(pending['students'], [])
        self.assertEqual(pending['missing'][0]['id'], 'x')
        self.assertEqual(pending['inactive'], 0)
        with self.assertRaises(ValueError): server.analyze(workbook([['x','A','T',.8,7,None,None]]), 4)

    def test_upload_endpoint(self):
        content = workbook([['a','Ana','A',.95,8,.9,7]])
        boundary = b'boundary-aede'
        payload = (b'--'+boundary+b'\r\nContent-Disposition: form-data; name="periodo"\r\n\r\n1\r\n'
                   b'--'+boundary+b'\r\nContent-Disposition: form-data; name="arquivo"; filename="alunos.xlsx"\r\n'
                   b'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
                   + content + b'\r\n--'+boundary+b'--\r\n')
        handler = object.__new__(server.Handler)
        handler.path='/api/analisar'; handler.rfile=BytesIO(payload); handler.wfile=BytesIO(); handler.headers=Message()
        handler.headers['Content-Type']='multipart/form-data; boundary=boundary-aede'; handler.headers['Content-Length']=str(len(payload))
        status=[]; handler.send_response=lambda code: status.append(code); handler.send_header=lambda *args: None; handler.end_headers=lambda: None
        handler.do_POST()
        self.assertEqual(status, [200])
        self.assertEqual(server.json.loads(handler.wfile.getvalue())['students'][0]['name'], 'Ana')

if __name__ == '__main__': unittest.main()
