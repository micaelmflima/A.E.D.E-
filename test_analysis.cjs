const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
global.XLSX=require('./vendor/xlsx.full.min.js');
require('./analysis.js');
const A=global.AedeAnalysis;
function read(text){const b=Buffer.from(text);return A.read(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),XLSX);}
for(const sep of [',',';','\t']){
 const rows=read([['Aluno_ID','Nome','Turma','Presença_1tri','Media_1tri'],['a','Ana','1A','"87,5%"','"7,2"']].map(r=>r.join(sep)).join('\n'));
 assert.equal(A.analyzeRows(rows,1).students[0].attendance,87.5);
}
assert.throws(()=>read('Aluno_ID,Aluno_ID,Nome,Turma,Presença_1tri,Media_1tri\na,a,A,T,.9,8'),/duplicadas/);
assert.throws(()=>read('Aluno_ID,Nome,Turma,Presença_1tri,Media_1tri\na,A,T,.9,8\na,B,T,.8,7'),/único/);
const rows=read('Aluno_ID,Nome,Turma,Presença_1tri,Media_1tri,Data_Corte_1tri,Data_Evasao\na,A,T,.9,8,2024-05-17,2024-05-17\nb,B,T,,,2024-05-17,');
assert.equal(A.analyzeRows(rows,1).inactive,1);assert.equal(A.analyzeRows(rows,1).missing.length,1);
const expectedPath=path.join(__dirname,'../tmp/base_2024/expected_analysis.json');
if(fs.existsSync(expectedPath)){
 const expected=JSON.parse(fs.readFileSync(expectedPath,'utf8'));
 for(const item of expected){
  const bytes=fs.readFileSync(path.join(__dirname,'../outputs/base_2024',item.file));
  const actual=A.analyzeRows(A.read(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),XLSX),item.period);
  assert.deepEqual(actual,item.result,`${item.file} trimestre ${item.period}`);
 }
 console.log('Paridade com Python: nove importações completas idênticas.');
}
const html=fs.readFileSync('index.html','utf8');
assert.doesNotMatch(html,/(?:src|href)="\/(?!\/)/);
assert.doesNotMatch(fs.readFileSync('app.js','utf8'),/fetch\(|\/api\//);
console.log('Leitura CSV, validações, datas e caminhos do Pages verificados.');
