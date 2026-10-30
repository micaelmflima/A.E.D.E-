# A.E.D.E. — MVP de acompanhamento estudantil

Aplicação local para importar planilhas `.xlsx`, visualizar indicadores experimentais e registrar ações de acompanhamento. Nenhuma planilha de estudantes é distribuída neste repositório.

## Executar

Requisitos: Python 3.10 ou superior, `numpy` e `openpyxl`.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Abra <http://127.0.0.1:8000> e importe uma planilha fictícia compatível. Selecione o trimestre desejado. O servidor aceita arquivos de até 12 MB; o processamento ocorre localmente e os uploads não são gravados. As anotações ficam no armazenamento do navegador.

Neste computador, também é possível iniciar pelo PowerShell com `./iniciar.ps1`, usando o Python e as bibliotecas disponíveis no ambiente do Codex. Mantenha a janela aberta enquanto usa o site; pressione Ctrl+C para encerrar.

## Formato da planilha

Use uma aba chamada `Alunos_Modelo`, `Alunos` ou `Estudantes`, com cabeçalhos na primeira linha e uma linha por estudante. As colunas obrigatórias são `Aluno_ID`, `Nome`, `Turma`, `Presença_1tri` e `Media_1tri`. Para analisar outros períodos, acrescente `Presença_2tri`, `Media_2tri`, `Presença_3tri` e `Media_3tri`. `Serie` é opcional. Frequência aceita proporção entre 0 e 1 ou percentual acima de 1 até 100; o valor 1 significa 100%. Médias devem estar entre 0 e 10. Identificadores precisam ser únicos. Estudantes sem valores válidos no período escolhido aparecem na lista de dados pendentes e não recebem pontuação.

## Como funciona

Uma regressão logística com coeficientes previamente treinados em uma base sintética usa frequência e média como entradas. A planilha de treinamento não está no repositório. O escore resultante é usado como indicador individual experimental. A comparação coletiva usa a queda média de notas da turma entre o trimestre anterior e o atual, se houver ao menos três registros comparáveis. Nesse caso, o indicador final é 80% individual e 20% coletivo; sem essa comparação, mostra-se apenas o individual. O limite de 30% na interface é uma referência inicial de demonstração, não um corte validado.

Os percentuais são indicadores experimentais, não probabilidades calibradas, diagnósticos ou decisões. A base usada no treinamento foi gerada artificialmente e não demonstra desempenho no mundo real; resultados nessa mesma base não são avaliação independente. O modelo usa apenas dois atributos e não reproduz a fórmula 2.0 integral, que não estava disponível. Aulas não ministradas, ausências consecutivas, justificativas e evolução recente da frequência ainda não integram o cálculo. A análise por trimestre usa a média do período completo, não uma leitura em tempo real. Não use dados reais nesta versão: ela não possui autenticação, permissões, segurança de produção ou validação clínica/pedagógica. Não use o resultado para decisões automáticas.

Quando a planilha inclui uma aba `Calendario` com `Data` e `Trimestre` e uma coluna `Data_Evasao`, estudantes que já saíram antes do início do período selecionado não são analisados naquele período. Registros que saem durante o trimestre precisam de revisão humana, pois os valores são consolidados por trimestre.
