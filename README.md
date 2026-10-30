# A.E.D.E. — MVP de acompanhamento estudantil

Aplicação local para importar arquivos `.xlsx` e `.csv`, visualizar indicadores experimentais e registrar ações de acompanhamento. A nova coorte fictícia de 2024 está em `../outputs/base_2024`, junto ao notebook e à metodologia.

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

No Excel, use uma aba chamada `Alunos_Modelo`, `Alunos`, `Estudantes` ou `Base_Completa`, com cabeçalhos na primeira linha e uma linha por estudante. No CSV, use a mesma tabela em UTF-8, com separador vírgula, ponto e vírgula ou tabulação. As colunas obrigatórias são `Aluno_ID`, `Nome`, `Turma`, `Presença_1tri` e `Media_1tri`. Para analisar outros períodos, acrescente `Presença_2tri`, `Media_2tri`, `Presença_3tri` e `Media_3tri`. `Serie` e `Ano_Referencia` são opcionais. Frequência aceita proporção entre 0 e 1, percentual acima de 1 até 100 ou texto explícito como `87,5%`; o valor numérico 1 significa 100%, enquanto `1%` significa um por cento. Médias devem estar entre 0 e 10. Identificadores precisam ser únicos, inclusive entre anos. Estudantes sem valores válidos no período escolhido aparecem na lista de dados pendentes e não recebem pontuação. O indicador coletivo separa as turmas por ano de referência.

## Como funciona

Uma regressão logística com coeficientes previamente treinados em uma base sintética usa frequência e média como entradas. A planilha de treinamento não está no repositório. O escore resultante é usado como indicador individual experimental. A comparação coletiva usa a queda média de notas da turma entre o trimestre anterior e o atual, se houver ao menos três registros comparáveis. Nesse caso, o indicador final é 80% individual e 20% coletivo; sem essa comparação, mostra-se apenas o individual. O limite de 30% na interface é uma referência inicial de demonstração, não um corte validado.

Os percentuais são indicadores experimentais, não probabilidades calibradas, diagnósticos ou decisões. A base usada no treinamento foi gerada artificialmente e não demonstra desempenho no mundo real; resultados nessa mesma base não são avaliação independente. O modelo usa apenas dois atributos e não reproduz a fórmula 2.0 integral, que não estava disponível. Aulas não ministradas, ausências consecutivas, justificativas e evolução recente da frequência ainda não integram o cálculo. A análise por trimestre usa a média do período completo, não uma leitura em tempo real. Não use dados reais nesta versão: ela não possui autenticação, permissões, segurança de produção ou validação clínica/pedagógica. Não use o resultado para decisões automáticas.

O recorte considera o fechamento do trimestre. No Excel, as datas vêm da aba `Calendario` (`Data`, `Trimestre`) e a saída pode vir da aba `Desfechos` (`Aluno_ID`, `Data_Evasao`) ou da tabela de alunos. No CSV, use `Data_Inicio_Ntri`, `Data_Corte_Ntri` e `Data_Evasao`, em `AAAA-MM-DD`. Estudantes cuja saída ocorreu até o corte não recebem índice naquele período; aparecem no total “fora do período”. Sem datas de corte, conserva-se apenas o filtro pelo início quando essa informação existe. Sem datas, não é possível determinar inatividade pela matrícula. O site processa apenas frequência e notas: colunas extras de questionário não são usadas como preditores.

Para esta entrega, importe `../outputs/base_2024/base_sintetica_ensino_medio_2024.xlsx`, `alunos_modelo.csv` ou `base_completa_alunos_questionario.csv`. O treino do notebook não substitui os coeficientes do site automaticamente. A avaliação completa da metodologia e as convenções estão em `../outputs/base_2024/LEIA_ME.md`.
