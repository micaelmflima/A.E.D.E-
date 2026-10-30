import unittest
from io import BytesIO
from email.message import Message
from openpyxl import Workbook
from datetime import date
import csv
from io import StringIO
import server

def workbook(rows):
    book = Workbook(); sheet = book.active; sheet.title = 'Alunos_Modelo'
    sheet.append(['Aluno_ID','Nome','Turma','Presença_1tri','Media_1tri','Presença_2tri','Media_2tri'])
    for row in rows: sheet.append(row)
    result = BytesIO(); book.save(result); return result.getvalue()

class AnalysisTests(unittest.TestCase):
    def test_csv_formats_and_percentages(self):
        for delimiter in (',', ';', '\t'):
            text = StringIO(newline='')
            writer = csv.writer(text, delimiter=delimiter)
            writer.writerow(['Aluno_ID','Nome','Turma','Presença_1tri','Media_1tri'])
            writer.writerow(['a','Ana; Silva','1A','87,5%','7,2'])
            result=server.analyze(text.getvalue().encode('utf-8-sig'),1)
            self.assertEqual(result['students'][0]['attendance'],87.5)
            self.assertEqual(result['students'][0]['grade'],7.2)

    def test_csv_inactive_at_period_end(self):
        content=('Aluno_ID,Nome,Turma,Ano_Referencia,Presença_1tri,Media_1tri,Data_Corte_1tri,Data_Evasao\n'
                 'a,Ana,1A,2024,.9,8,2024-05-17,2024-05-17\n'
                 'b,Bia,1A,2024,.8,7,2024-05-17,2024-05-18\n').encode()
        result=server.analyze(content,1)
        self.assertEqual(result['inactive'],1)
        self.assertEqual([s['id'] for s in result['students']],['b'])
        self.assertEqual(result['years'],['2024'])

    def test_excel_calendar_and_outcomes(self):
        book=Workbook(); sheet=book.active; sheet.title='Alunos_Modelo'
        sheet.append(['Aluno_ID','Nome','Turma','Presença_1tri','Media_1tri'])
        sheet.append(['a','Ana','1A',.9,8]); sheet.append(['b','Bia','1A',.9,8])
        cal=book.create_sheet('Calendario'); cal.append(['Data','Trimestre'])
        cal.append([date(2024,2,5),1]); cal.append([date(2024,5,17),1])
        outcomes=book.create_sheet('Desfechos'); outcomes.append(['Aluno_ID','Data_Evasao'])
        outcomes.append(['a',date(2024,5,17)]); outcomes.append(['b',None])
        stream=BytesIO(); book.save(stream)
        result=server.analyze(stream.getvalue(),1)
        self.assertEqual(result['inactive'],1)
        self.assertEqual(result['students'][0]['year'],'2024')

    def test_class_context_does_not_mix_years(self):
        text=StringIO(newline=''); writer=csv.writer(text)
        writer.writerow(['Aluno_ID','Nome','Turma','Ano_Referencia','Presença_1tri','Media_1tri','Presença_2tri','Media_2tri'])
        for year,delta in [(2023,0),(2024,3)]:
            for i in range(3): writer.writerow([f'{year}-{i}','Nome','1A',year,.9,8,.9,8-delta])
        result=server.analyze(text.getvalue().encode(),2)
        self.assertEqual({s['context'] for s in result['students'] if s['year']=='2023'},{0.0})
        self.assertEqual({s['context'] for s in result['students'] if s['year']=='2024'},{100.0})

    def test_csv_rejects_duplicate_headers_bad_dates_and_wrong_table(self):
        for text in ['Aluno_ID,Aluno_ID,Nome,Turma,Presença_1tri,Media_1tri\na,a,A,T,.9,7\n',
                     'Aluno_ID,Nome,Turma,Presença_1tri,Media_1tri,Data_Evasao\na,A,T,.9,7,17/05/2024\n',
                     'Aluno_ID,Data,Trimestre\na,2024-02-05,1\n']:
            with self.assertRaises(ValueError): server.analyze(text.encode(),1)

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
