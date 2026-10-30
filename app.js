const $ = s => document.querySelector(s);
let data = [], selected = null, activeFile = null, datasetKey = '', requestNumber = 0;
const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = n => `${Number(n).toLocaleString('pt-BR',{maximumFractionDigits:1})}%`;
function render(){
 const q=$('#search').value.toLocaleLowerCase('pt-BR').trim(), cls=$('#class-filter').value, f=$('#filter').value;
 const filtered=data.filter(x=>`${x.name} ${x.id} ${x.class}`.toLocaleLowerCase('pt-BR').includes(q)&&(!cls||x.class===cls)&&(f==='all'||(f==='attention'?x.score>=30:x.score<30)));
 $('#rows').innerHTML=filtered.length?filtered.map(x=>`<tr><td><div class="student"><span class="avatar">${esc(x.name.charAt(0).toUpperCase())}</span><div><strong>${esc(x.name)}</strong><small>${esc(x.id)}</small></div></div></td><td>${esc(x.class)}</td><td>${pct(x.attendance)}</td><td>${x.grade.toLocaleString('pt-BR')}</td><td><div class="score"><span class="track"><i style="width:${x.score}%"></i></span><strong>${pct(x.score)}</strong></div></td><td><button class="view" data-id="${esc(x.id)}" aria-label="Ver detalhes de ${esc(x.name)}">Ver detalhes <span>→</span></button></td></tr>`).join(''):`<tr><td colspan="6"><div class="empty"><div>⌕</div><strong>Nenhum estudante encontrado</strong><p>${data.length?'Tente ajustar os filtros ou a busca.':'Não há indicadores disponíveis para este período.'}</p></div></td></tr>`;
 $('#count').textContent=`${filtered.length} de ${data.length} estudantes`;
}
async function analyze(){
 const request=++requestNumber;
 data=[];selected=null;if($('#dialog').open)$('#dialog').close();
 $('#total').textContent=$('#attention').textContent=$('#frequency').textContent='—';
 $('#period-label').textContent=activeFile?'Analisando...':'Aguardando planilha';
 $('#skipped').textContent='';$('#pending').hidden=true;$('#error').textContent='';
 $('#class-filter').innerHTML='<option value="">Todas as turmas</option>';$('#class-filter').value='';render();
 if(!activeFile){$('#file-name').textContent='Nenhum arquivo selecionado';return;}
 $('#file-name').textContent='Analisando planilha...';
 const form=new FormData();form.append('arquivo',activeFile);form.append('periodo',$('#period').value);
 try{const response=await fetch('/api/analisar',{method:'POST',body:form});const result=await response.json();if(request!==requestNumber)return;if(!response.ok)throw Error(result.error);data=result.students;
 $('#file-name').textContent=`✓ ${activeFile.name}`;$('#period-label').textContent=`${result.period}º trimestre`;
 $('#total').textContent=data.length;$('#attention').textContent=data.filter(x=>x.score>=30).length;
 $('#frequency').textContent=data.length?pct(data.reduce((n,x)=>n+x.attendance,0)/data.length):'—';
 $('#skipped').textContent=result.inactive?`${result.inactive} fora do período`:'';
 $('#pending').hidden=!result.missing.length;$('#pending').open=false;$('#pending-title').textContent=`${result.missing.length} estudante(s) com dados pendentes`;
 $('#pending-list').innerHTML=result.missing.map(x=>`<li><strong>${esc(x.name)}</strong> <span>${esc(x.id)} · ${esc(x.class)}</span></li>`).join('');
 $('#class-filter').innerHTML='<option value="">Todas as turmas</option>'+[...new Set(data.map(x=>x.class))].sort().map(x=>`<option>${esc(x)}</option>`).join('');render();
 }catch(e){if(request!==requestNumber)return;$('#error').textContent=e.message;$('#file-name').textContent='Não foi possível analisar o arquivo.';data=[];$('#total').textContent=$('#attention').textContent=$('#frequency').textContent='—';$('#period-label').textContent='Aguardando planilha';$('#skipped').textContent='';$('#pending').hidden=true;render();}
}
$('#file').addEventListener('change',e=>{activeFile=e.target.files[0];datasetKey=activeFile?`${activeFile.name}:${activeFile.size}:${activeFile.lastModified}`:'';analyze()});$('#period').addEventListener('change',analyze);['#search','#class-filter','#filter'].forEach(s=>$(s).addEventListener('input',render));
$('#rows').addEventListener('click',e=>{const b=e.target.closest('[data-id]');if(!b)return;selected=data.find(x=>x.id===b.dataset.id);const s=selected;
 $('#detail-name').textContent=s.name;$('#detail-id').textContent=`${s.id} · ${s.class} ${s.series}`;
 $('#detail-body').innerHTML=`<div class="detail-score"><div><small>ÍNDICE DE ATENÇÃO</small><strong>${pct(s.score)}</strong><p>Resultado experimental para apoiar a análise.</p></div><div class="round">${pct(s.score)}</div></div><div class="detail-grid"><div><small>FREQUÊNCIA</small><strong>${pct(s.attendance)}</strong></div><div><small>MÉDIA ATUAL</small><strong>${s.grade.toLocaleString('pt-BR')}</strong></div><div><small>MÉDIA ANTERIOR</small><strong>${s.priorGrade===null?'Não disponível':s.priorGrade.toLocaleString('pt-BR')}</strong></div></div><div class="explanation"><strong>Como ler este indicador</strong><p>O modelo identifica padrões de frequência e notas em uma base fictícia. Resultado individual: ${pct(s.model)}. ${s.context===null?'Comparação coletiva indisponível; o índice mostra apenas o resultado individual.':`Indicador coletivo da turma: ${pct(s.context)}. O índice combina 80% individual e 20% coletivo.`}</p><p>Os números não são uma chance comprovada de evasão. Confira os dados e converse com o estudante antes de agir.</p></div>`;
 try{$('#note').value=localStorage.getItem('aede:note:'+datasetKey+':'+s.id)||''}catch{$('#note').value=''};$('#saved').textContent='';$('#dialog').showModal();});
$('#close').onclick=()=>$('#dialog').close();$('#dialog').addEventListener('click',e=>{if(e.target===$('#dialog'))$('#dialog').close()});
$('#save-note').onclick=()=>{try{localStorage.setItem('aede:note:'+datasetKey+':'+selected.id,$('#note').value);$('#saved').textContent='Salvo neste navegador.'}catch{$('#saved').textContent='Não foi possível salvar.'}};
