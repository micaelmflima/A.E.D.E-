// Teste da lógica da interface com elementos simulados; não substitui teste visual.
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ids=['search','class-filter','filter','rows','error','file-name','period','period-label','total','attention','frequency','skipped','pending','pending-title','pending-list','file','detail-name','detail-id','detail-body','note','saved','dialog','close','save-note','count'];
const elements=Object.fromEntries(ids.map(id=>[id,{value:'',textContent:'',innerHTML:'',hidden:false,open:false,events:{},addEventListener(name,fn){this.events[name]=fn},showModal(){this.open=true},close(){this.open=false}}]));
elements['period'].value='1';elements['filter'].value='all';
const stored={};let result;
const ctx={document:{querySelector:s=>elements[s.slice(1)]},AedeAnalysis:{analyze:async()=>result},localStorage:{getItem:k=>stored[k]||null,setItem:(k,v)=>{stored[k]=v}},console};
vm.createContext(ctx);vm.runInContext(readFileSync('app.js','utf8'),ctx);
const one={id:'X1',name:'Ana & Silva',class:'1A',series:'1º',year:'2024',attendance:80,grade:6,priorGrade:null,score:34,model:34,context:null};
async function run(){
 result={students:[one],missing:[{id:'X2',name:'Bia <Teste>',class:'1A'}],inactive:0,period:1,years:['2024']};
 await elements.file.events.change({target:{files:[{name:'demo.xlsx',size:22,lastModified:7}]}});
 // The file handler starts an async operation without returning it.
 await new Promise(setImmediate);
 assert.equal(elements.total.textContent,1);assert.equal(elements.attention.textContent,1);
 assert.equal(elements['period-label'].textContent,'2024 · 1º trimestre');
 assert.equal(elements.pending.hidden,false);assert.match(elements['pending-list'].innerHTML,/Bia &lt;Teste&gt;/);
 assert.match(elements.rows.innerHTML,/Ana &amp; Silva/);
 elements.search.value='inexistente';elements.search.events.input();assert.match(elements.rows.innerHTML,/Nenhum estudante encontrado/);
 elements.search.value='';elements.search.events.input();
 elements.rows.events.click({target:{closest:()=>({dataset:{id:'X1'}})}});
 assert.equal(elements.dialog.open,true);assert.equal(elements['detail-name'].textContent,'Ana & Silva');
 assert.match(elements['detail-id'].textContent,/2024/);
 elements.note.value='Conversar com o estudante';elements['save-note'].onclick();assert.match(elements.saved.textContent,/Salvo/);
 let finish;ctx.AedeAnalysis.analyze=()=>new Promise(resolve=>{finish=resolve});
 elements.file.events.change({target:{files:[{name:'outra.xlsx',size:12,lastModified:8}]}});
 assert.equal(elements.dialog.open,false);assert.equal(elements.total.textContent,'—');assert.doesNotMatch(elements.rows.innerHTML,/Ana/);
 finish({students:[one],missing:[],inactive:0,period:1});await new Promise(setImmediate);
 ctx.AedeAnalysis.analyze=async()=>result;
 result={students:[],missing:[{id:'X2',name:'Bia',class:'1A'}],inactive:0,period:2};
 elements.period.value='2';await elements.period.events.change();
 assert.equal(elements.frequency.textContent,'—');assert.match(elements.rows.innerHTML,/Não há indicadores disponíveis/);
 console.log('Interface: importação, pendências, busca, detalhes e anotação verificadas.');
}
run().catch(err=>{console.error(err);process.exitCode=1});
