"""Servidor local de demonstração; os arquivos enviados são processados em memória."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from io import BytesIO, StringIO
from datetime import date, datetime
import csv
import json
import mimetypes
import unicodedata
import zipfile
import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 12 * 1024 * 1024

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').strip().lower()) if not unicodedata.combining(c)).replace(' ', '_')

def number(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        v = float(str(value).replace(',', '.'))
        return v if np.isfinite(v) else None
    except (ValueError, TypeError):
        return None

def iso_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    if value is None or str(value).strip() == '':
        return None
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError('Use datas no formato AAAA-MM-DD nas colunas de período e Data_Evasao.') from exc


def students(content):
    if len(content) > MAX_UPLOAD:
        raise ValueError('O arquivo deve ter no máximo 12 MB.')
    book = None
    try:
        starts, ends, outcomes = {}, {}, {}
        if content.startswith(b'PK'):
            with zipfile.ZipFile(BytesIO(content)) as archive:
                if sum(x.file_size for x in archive.infolist()) > 80 * 1024 * 1024:
                    raise ValueError('A planilha descompactada é grande demais.')
            book = load_workbook(BytesIO(content), read_only=True, data_only=True)
            sheet = next((s for s in book if norm(s.title) in ('alunos_modelo', 'alunos', 'estudantes', 'base_completa')), None)
            if sheet is None:
                raise ValueError('Não encontrei a aba Alunos_Modelo, Alunos, Estudantes ou Base_Completa.')
            rows = sheet.iter_rows(values_only=True)
            calendar = next((s for s in book if norm(s.title) == 'calendario'), None)
            if calendar:
                cal_rows = calendar.iter_rows(values_only=True)
                cal_header = [norm(x) for x in next(cal_rows, [])]
                for values in cal_rows:
                    item = dict(zip(cal_header, values))
                    period, day = number(item.get('trimestre')), iso_date(item.get('data'))
                    if period in (1, 2, 3) and day:
                        year = day[:4]
                        key = (year, int(period))
                        starts[key] = min(starts.get(key, day), day)
                        ends[key] = max(ends.get(key, day), day)
            outcome_sheet = next((s for s in book if norm(s.title) == 'desfechos'), None)
            if outcome_sheet:
                outcome_rows = outcome_sheet.iter_rows(values_only=True)
                outcome_header = [norm(x) for x in next(outcome_rows, [])]
                for values in outcome_rows:
                    item = dict(zip(outcome_header, values))
                    ident = str(item.get('aluno_id') or '').strip()
                    if not ident or ident in outcomes:
                        raise ValueError('A aba Desfechos precisa de Aluno_ID único e preenchido.')
                    outcomes[ident] = iso_date(item.get('data_evasao'))
        else:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError as exc:
                raise ValueError('Salve o CSV na codificação UTF-8.') from exc
            if '\x00' in text:
                raise ValueError('Selecione um arquivo .xlsx ou .csv válido.')
            try:
                dialect = csv.Sniffer().sniff(text[:65536], delimiters=',;\t')
            except csv.Error as exc:
                raise ValueError('CSV inválido: use vírgula, ponto e vírgula ou tabulação como separador.') from exc
            rows = csv.reader(StringIO(text, newline=''), dialect=dialect, strict=True)
        header = [norm(x) for x in next(rows, [])]
        if len(set(header)) != len(header):
            raise ValueError('A planilha contém colunas duplicadas.')
        required = {'aluno_id', 'nome', 'turma', 'presenca_1tri', 'media_1tri'}
        missing = required - set(header)
        if missing:
            raise ValueError('Colunas obrigatórias ausentes: ' + ', '.join(sorted(missing)))
        data = []
        for values in rows:
            if not any(v is not None and str(v).strip() for v in values): continue
            if len(values) != len(header):
                raise ValueError('Há linhas com quantidade de campos diferente do cabeçalho.')
            data.append(dict(zip(header, values)))
            if len(data) > 10000: raise ValueError('A planilha deve conter entre 1 e 10.000 estudantes.')
        if not data:
            raise ValueError('A planilha deve conter entre 1 e 10.000 estudantes.')
        ids = [str(r.get('aluno_id') or '').strip() for r in data]
        if any(not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError('Cada estudante precisa de um Aluno_ID único e preenchido.')
        for row in data:
            row['aluno_id'] = str(row['aluno_id']).strip()
            year = str(row.get('ano_referencia') or '')
            if year.endswith('.0'): year = year[:-2]
            row['ano_referencia'] = year
            row['_period_starts'] = {t: iso_date(row.get(f'data_inicio_{t}tri')) or starts.get((year,t)) for t in (1,2,3)}
            row['_period_ends'] = {t: iso_date(row.get(f'data_corte_{t}tri')) or ends.get((year,t)) for t in (1,2,3)}
            # Excel legado com um único ano no calendário pode omitir Ano_Referencia.
            if not year and len({k[0] for k in starts}) == 1:
                year = next(iter(starts))[0]
                row['ano_referencia'] = year
                row['_period_starts'] = {t: starts.get((year,t)) for t in (1,2,3)}
                row['_period_ends'] = {t: ends.get((year,t)) for t in (1,2,3)}
            left = iso_date(row.get('data_evasao'))
            if row['aluno_id'] in outcomes:
                if left and left != outcomes[row['aluno_id']]:
                    raise ValueError('Data_Evasao diverge entre a aba de alunos e Desfechos.')
                left = outcomes[row['aluno_id']]
            row['data_evasao'] = left
        return data
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Não foi possível ler o arquivo. Confira se é um .xlsx ou .csv válido.') from exc
    finally:
        if book is not None: book.close()

def features(row, period):
    raw = row.get(f'presenca_{period}tri')
    explicit_percent = isinstance(raw, str) and raw.strip().endswith('%')
    f = number(raw.strip()[:-1] if explicit_percent else raw)
    g = number(row.get(f'media_{period}tri'))
    if f is not None and (explicit_percent or 1 < f <= 100): f /= 100
    if f is None or g is None or not (0 <= f <= 1 and 0 <= g <= 10):
        return None
    return [f, g / 10]

# Coeficientes da regressão logística experimental treinada anteriormente em
# dados sintéticos; nenhuma linha da planilha de treinamento é distribuída.
WEIGHTS = np.array([0.3606146743291433, -3.232010714396841, -0.3487609626058542])


def inactive_at_cutoff(row, period):
    left = row.get('data_evasao')
    end = row['_period_ends'].get(period)
    start = row['_period_starts'].get(period)
    return bool(left and ((end and left <= end) or (not end and start and left <= start)))


def group_key(row):
    return (row['ano_referencia'], str(row.get('turma') or 'Sem turma'))

def analyze(content, period):
    if period not in (1, 2, 3): raise ValueError('Escolha um trimestre válido.')
    rows = students(content)
    # Queda média só inclui registros com os dois períodos disponíveis.
    groups = {}
    for row in rows:
        now, prev = features(row, period), features(row, period-1) if period > 1 else None
        if inactive_at_cutoff(row, period): continue
        if now and prev:
            groups.setdefault(group_key(row), []).append(prev[1] - now[1])
    output, missing, inactive = [], [], 0
    for row in rows:
        now = features(row, period)
        if inactive_at_cutoff(row, period):
            inactive += 1
            continue
        if not now:
            missing.append({'id': str(row['aluno_id']), 'name': str(row.get('nome') or 'Sem nome'),
                            'class': str(row.get('turma') or 'Sem turma')})
            continue
        prev = features(row, period-1) if period > 1 else None
        group = str(row.get('turma') or 'Sem turma')
        ml = float(1 / (1 + np.exp(-np.clip(np.dot([1, *now], WEIGHTS), -30, 30)))) * 100
        deltas = groups.get(group_key(row), [])
        # Queda coletiva é contextual e só existe com observações suficientes.
        context = min(100, max(0, float(np.mean(deltas)) * 500)) if len(deltas) >= 3 else None
        score = .8 * ml + .2 * context if context is not None else ml
        output.append({'id':str(row['aluno_id']), 'name':str(row.get('nome') or 'Sem nome'),
          'class':group, 'series':str(row.get('serie') or ''), 'year':row['ano_referencia'], 'attendance':round(now[0]*100,1),
          'grade':round(now[1]*10,2), 'priorGrade':round(prev[1]*10,2) if prev else None,
          'score':round(score,1), 'model':round(ml,1), 'context':round(context,1) if context is not None else None})
    output.sort(key=lambda r: (-r['score'], r['name']))
    missing.sort(key=lambda r: (r['name'], r['id']))
    return {'students':output, 'missing':missing, 'inactive':inactive, 'total':len(rows),
            'skipped':len(missing)+inactive, 'period':period,
            'years':sorted({r['ano_referencia'] for r in rows if r['ano_referencia']})}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {'/': 'index.html', '/index.html':'index.html', '/app.js':'app.js', '/analysis.js':'analysis.js', '/vendor/xlsx.full.min.js':'vendor/xlsx.full.min.js', '/style.css':'style.css', '/logo.png':'logo.png'}
        target = routes.get(self.path.split('?')[0])
        if not target: self.send_error(404); return
        data = (ROOT / target).read_bytes()
        self.send_response(200); self.send_header('Content-Type', mimetypes.guess_type(target)[0] or 'application/octet-stream'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if self.path != '/api/analisar': self.send_error(404); return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > MAX_UPLOAD + 65536: raise ValueError('Arquivo vazio ou maior que 12 MB.')
            msg = BytesParser(policy=default).parsebytes(('Content-Type: '+self.headers.get('Content-Type','')+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+self.rfile.read(length))
            if not msg.is_multipart(): raise ValueError('Selecione um arquivo Excel ou CSV.')
            parts = {p.get_param('name', header='content-disposition'):p.get_payload(decode=True) for p in msg.iter_parts()}
            result = analyze(parts.get('arquivo', b''), int(parts.get('periodo', b'1')))
            self.respond(200, result)
        except (ValueError, TypeError) as exc: self.respond(400, {'error':str(exc)})
        except Exception: self.respond(500, {'error':'Não foi possível analisar a planilha.'})
    def respond(self, status, data):
        body=json.dumps(data, ensure_ascii=False).encode('utf-8'); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == '__main__':
    print('A.E.D.E. disponível em http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
