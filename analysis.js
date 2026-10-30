/* Análise local: nenhum arquivo de estudante é enviado a um servidor. */
(function(root){
 'use strict';
 const norm=v=>String(v??'').trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/ /g,'_');
 const number=v=>v==null||String(v).trim()===''?null:(Number.isFinite(Number(String(v).replace(',','.')))?Number(String(v).replace(',','.')):null);
 const day=v=>{
  if(v==null||v==='')return null;
  if(v instanceof Date)return v.toISOString().slice(0,10);
  const s=String(v).trim().slice(0,10);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(s)||Number.isNaN(Date.parse(s))||new Date(s).toISOString().slice(0,10)!==s)throw Error('Use datas no formato AAAA-MM-DD.');
  return s;
 };
 function table(sheet,XLSX){
  const matrix=XLSX.utils.sheet_to_json(sheet,{header:1,defval:null,raw:true,blankrows:false});
  const header=(matrix.shift()||[]).map(norm);
  if(new Set(header).size!==header.length)throw Error('A planilha contém colunas duplicadas.');
  return {header,rows:matrix.filter(r=>r.some(v=>v!=null&&String(v).trim()!=='')).map(r=>Object.fromEntries(header.map((k,i)=>[k,r[i]??null])))};
 }
 function read(buffer,XLSX){
  if(buffer.byteLength>12*1024*1024)throw Error('O arquivo deve ter no máximo 12 MB.');
  const bytes=new Uint8Array(buffer), excel=bytes[0]===80&&bytes[1]===75;
  let book;
  if(excel){
   // Check declared ZIP sizes before asking the parser to decompress the file.
   const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let size=0;
   for(let i=0;i+46<=bytes.length;i++)if(view.getUint32(i,true)===0x02014b50){size+=view.getUint32(i+24,true);i+=45+view.getUint16(i+28,true)+view.getUint16(i+30,true)+view.getUint16(i+32,true);}
   if(size>80*1024*1024)throw Error('A planilha descompactada é grande demais.');
   book=XLSX.read(buffer,{type:'array',cellDates:true});
  }else{
   let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes).replace(/^\uFEFF/,'');}catch{throw Error('Salve o CSV na codificação UTF-8.');}
   if(text.includes('\0'))throw Error('Selecione um arquivo .xlsx ou .csv válido.');
   book=XLSX.read(text,{type:'string',raw:true});
  }
  const find=names=>book.SheetNames.find(s=>names.includes(norm(s)));
  const name=excel?find(['alunos_modelo','alunos','estudantes','base_completa']):book.SheetNames[0];
  if(!name)throw Error('Não encontrei a aba Alunos_Modelo, Alunos, Estudantes ou Base_Completa.');
  const {header,rows}=table(book.Sheets[name],XLSX);
  const missing=['aluno_id','nome','turma','presenca_1tri','media_1tri'].filter(k=>!header.includes(k));
  if(missing.length)throw Error('Colunas obrigatórias ausentes: '+missing.join(', '));
  if(!rows.length||rows.length>10000)throw Error('A planilha deve conter entre 1 e 10.000 estudantes.');
  const ids=new Set(), starts={},ends={},outcomes=new Map();
  const calendar=find(['calendario']);
  if(calendar)for(const r of table(book.Sheets[calendar],XLSX).rows){
   const t=number(r.trimestre),d=day(r.data);if(![1,2,3].includes(t)||!d)continue;
   const key=d.slice(0,4)+':'+t;starts[key]=!starts[key]||d<starts[key]?d:starts[key];ends[key]=!ends[key]||d>ends[key]?d:ends[key];
  }
  const outcome=find(['desfechos']);
  if(outcome)for(const r of table(book.Sheets[outcome],XLSX).rows){const id=String(r.aluno_id??'').trim();if(!id||outcomes.has(id))throw Error('A aba Desfechos precisa de Aluno_ID único e preenchido.');outcomes.set(id,day(r.data_evasao));}
  const years=[...new Set(Object.keys(starts).map(k=>k.split(':')[0]))];
  for(const r of rows){
   r.aluno_id=String(r.aluno_id??'').trim();if(!r.aluno_id||ids.has(r.aluno_id))throw Error('Cada estudante precisa de um Aluno_ID único e preenchido.');ids.add(r.aluno_id);
   r.ano_referencia=String(r.ano_referencia??'').replace(/\.0$/,'');if(!r.ano_referencia&&years.length===1)r.ano_referencia=years[0];
   r.starts={};r.ends={};for(const t of [1,2,3]){r.starts[t]=day(r['data_inicio_'+t+'tri'])||starts[r.ano_referencia+':'+t];r.ends[t]=day(r['data_corte_'+t+'tri'])||ends[r.ano_referencia+':'+t];}
   r.data_evasao=day(r.data_evasao);
   if(outcomes.has(r.aluno_id)){if(r.data_evasao&&r.data_evasao!==outcomes.get(r.aluno_id))throw Error('Data_Evasao diverge entre alunos e Desfechos.');r.data_evasao=outcomes.get(r.aluno_id);}
  }
  return rows;
 }
 function features(r,t){let raw=r['presenca_'+t+'tri'],explicit=typeof raw==='string'&&raw.trim().endsWith('%');let f=number(explicit?raw.trim().slice(0,-1):raw),g=number(r['media_'+t+'tri']);if(f!==null&&(explicit||(f>1&&f<=100)))f/=100;return f!==null&&g!==null&&f>=0&&f<=1&&g>=0&&g<=10?[f,g/10]:null;}
 const inactive=(r,t)=>Boolean(r.data_evasao&&((r.ends[t]&&r.data_evasao<=r.ends[t])||(!r.ends[t]&&r.starts[t]&&r.data_evasao<=r.starts[t])));
 const group=r=>JSON.stringify([r.ano_referencia,String(r.turma||'Sem turma')]);
 const round=(v,n)=>Math.round((v+Number.EPSILON)*10**n)/10**n;
 function analyzeRows(rows,t){
  if(![1,2,3].includes(t))throw Error('Escolha um trimestre válido.');
  const groups=new Map();for(const r of rows){const now=features(r,t),prev=t>1?features(r,t-1):null;if(!inactive(r,t)&&now&&prev){const key=group(r);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(prev[1]-now[1]);}}
  const students=[],missing=[];let count=0;
  for(const r of rows){if(inactive(r,t)){count++;continue;}const now=features(r,t);if(!now){missing.push({id:r.aluno_id,name:String(r.nome||'Sem nome'),class:String(r.turma||'Sem turma')});continue;}
   const prev=t>1?features(r,t-1):null,delta=groups.get(group(r))||[];
   const model=100/(1+Math.exp(-Math.max(-30,Math.min(30,.3606146743291433-3.232010714396841*now[0]-.3487609626058542*now[1]))));
   const context=delta.length>=3?Math.max(0,Math.min(100,delta.reduce((a,b)=>a+b,0)/delta.length*500)):null;
   students.push({id:r.aluno_id,name:String(r.nome||'Sem nome'),class:String(r.turma||'Sem turma'),series:String(r.serie??''),year:r.ano_referencia,attendance:round(now[0]*100,1),grade:round(now[1]*10,2),priorGrade:prev?round(prev[1]*10,2):null,score:round(context===null?model:.8*model+.2*context,1),model:round(model,1),context:context===null?null:round(context,1)});
  }
  students.sort((a,b)=>b.score-a.score||(a.name<b.name?-1:a.name>b.name?1:0));missing.sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:a.id.localeCompare(b.id));
  return {students,missing,inactive:count,total:rows.length,skipped:missing.length+count,period:t,years:[...new Set(rows.map(r=>r.ano_referencia).filter(Boolean))].sort()};
 }
 root.AedeAnalysis={read,analyzeRows,async analyze(file,t){if(!root.XLSX)throw Error('Não foi possível carregar o leitor de planilhas. Recarregue a página.');return analyzeRows(read(await file.arrayBuffer(),root.XLSX),Number(t));}};
})(globalThis);
