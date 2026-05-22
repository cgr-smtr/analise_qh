# 📊 Análise da Operação de Linhas de Ônibus

Este projeto é uma ferramenta reativa e profissional desenvolvida em **Python Streamlit** para a análise, comparação e validação de programações horárias (Quadros Horários - QH) de linhas de ônibus frente a dados oficiais de especificação de trânsito em formato **GTFS (General Transit Feed Specification)**. 

Originalmente desenvolvido em **R Shiny** ([1.1 app_format_qh.R](file:///c:/Users/arauj/OneDrive/Documents/Projetos/analise_qh/codigos/1.1%20app_format_qh.R)), o painel foi completamente migrado para Python seguindo princípios de arquitetura limpa, alta performance, segurança de tipos e cobertura abrangente de testes unitários. O código original em R foi preservado intacto.

---

## 🌟 Funcionalidades e Regras de Negócio Implementadas

### 1. Detecção Inteligente e Suporte Dual de Modo (Frequencies vs. Timetable)
A aplicação analisa dinamicamente o arquivo GTFS (ZIP) fornecido e detecta a presença de tabelas de horários operacionais:
* **Modo Frequências (`GTFSMode.FREQUENCIES`):** Baseia-se na tabela `frequencies.txt`. A ferramenta extrai as viagens baseadas em faixas horárias e headways, gerando as partidas individuais a partir de `range(start_time, end_time, headway_secs)`.
* **Modo Quadro Horário (`GTFSMode.TIMETABLE`):** Baseia-se na tabela `stop_times.txt`. A ferramenta extrai as viagens individuais mapeando-as pela primeira parada operacional de cada viagem (menor `stop_sequence`), identificando o horário de partida na origem da linha.

### 2. Parseador Robusto de Propostas com Rollover de Meia-Noite
O usuário pode colar uma listagem de horários propostos diretamente na interface em formato de um horário por linha (`HH:MM:SS`). O parser realiza:
* **Validação de Formato:** Validação rígida com expressão regular para garantir integridade e acusar erros imediatamente na tela caso caracteres inválidos sejam inseridos.
* **Tratamento de Rollover (Virada de Dia):** Caso um horário subsequente na lista colada apresente valor menor que o anterior, o parser detecta de forma reativa que houve a transição da meia-noite (24h) e adiciona automaticamente `86.400 segundos` (e assim acumulando para dias operacionais estendidos), replicando fielmente o comportamento das operações noturnas e madrugadas.

### 3. Algoritmo de Matching Comparativo (1:1)
O coração estatístico da ferramenta pareia as partidas extraídas do GTFS com os horários propostos pelo usuário utilizando a técnica de vizinhos mais próximos arredondada ao minuto (`difftime`):
* **Resolução de Conflitos e Colisões:** Para evitar que uma única partida do GTFS seja associada a múltiplos horários propostos próximos (ou vice-versa), o algoritmo aplica filtros e validações bidirecionais ordenadas, garantindo que o pareamento 1:1 seja único e matematicamente correto.
* **Indicadores de Desempenho:** Indica graficamente na tabela de comparação se o intervalo (headway) da proposta é maior (`↑`), menor (`↓`) ou igual (`=`) ao do GTFS correspondente.

### 4. Resumo e Estatísticas por Faixa Operacional
Gera um consolidado contendo a contagem exata de partidas por período de serviço (faixas de 1 hora e períodos de pico agregados), permitindo uma visão macro rápida de onde as alterações na programação proposta estão concentradas em relação ao GTFS planejado, incluindo uma linha final de soma total de partidas.

### 5. Exportação Inteligente de Dados
Disponibiliza botões de download independentes na barra lateral para salvar os dados em disco, adaptando-se ao tipo de dado que está sendo analisado:
* **Downloads com Prefixo Unificado:** Todos os nomes de arquivos gerados utilizam o padrão unificado `horarios_<linha>_<destino>_<calendario>.<extensao>` (tanto para GTFS quanto para a Proposta do Usuário, em `.csv` ou `.txt`).
* **Exportação no Modo Frequência (CSV):** Gera um arquivo `.csv` contendo as frequências reagrupadas em blocos contínuos (`trip_id, trip_headsign, trip_short_name, start_time, end_time, headway_secs`). A proposta do usuário é reconstruída de forma robusta e transparente na hora do download a partir de seus segundos (ordenando e removendo duplicatas), garantindo total consistência com os blocos de frequências do GTFS.
* **Exportação no Modo Timetable (TXT):** Gera um arquivo de texto simples contendo uma partida ordenada por linha, sem cabeçalho (ideal para cópia e colagem rápida de volta para outros sistemas ou planilhas).

---

## 🎨 Design System e Polimento Visual (Aesthetics)

O painel utiliza princípios visuais modernos com total suporte a recursos adaptáveis do Streamlit:
* **Fidelidade de Cores por Faixa Horária:** Utiliza uma paleta pastel harmoniosa (definida em [config.py](file:///c:/Users/arauj/OneDrive/Documents/Projetos/analise_qh/app/config.py)) que colore as células de horários dependendo da hora do dia, facilitando a identificação visual rápida de turnos e picos de operação.
* **Suporte Nativo a Tema Claro e Escuro (Dark Mode):** O estilo das tabelas HTML e cabeçalhos utiliza fundos semitransparentes baseados em variáveis nativas do Streamlit (como `var(--text-color)` e `rgba(128,128,128,0.15)`). As tabelas alteram automaticamente suas cores de texto e linhas divisórias, eliminando problemas de legibilidade comuns em temas pretos/escuros.
* **Sanitização de Strings HTML:** O renderizador remove recuos em excesso de strings multilinhas antes de enviá-las ao Streamlit, contornando limitações do parser Markdown do Streamlit que transformava elementos HTML em blocos brancos de código em Markdown.

---

## 📁 Estrutura de Diretórios do Projeto

A separação de responsabilidades assegura a facilidade de manutenção e extensibilidade da base de código:

```
analise_qh/
├── app/                                  # Código-fonte Python
│   ├── main.py                           # Ponto de entrada Streamlit (UI e reatividade)
│   ├── config.py                         # Constantes globais (cores, quebras de faixa horária, Enums)
│   ├── gtfs_loader.py                    # Leitura de ZIP com cache, extração de filtros e trips
│   ├── schedule_extractor.py             # Processador de horários a partir de frequencies/stop_times
│   ├── user_input_parser.py              # Leitor e validador de horários colados (com rollover de 24h)
│   ├── comparison_engine.py              # Algoritmo de matching 1:1 e agregador de resumos
│   ├── export_handler.py                 # Gerador de arquivos CSV (frequências agrupadas) e TXT (horários)
│   └── ui_components.py                  # Renderizador de tabelas estilizadas e limpas para HTML
├── codigos/                              # Local de conservação do código original
│   └── 1.1 app_format_qh.R               # Script original em R Shiny (mantido intacto)
├── tests/                                # Suíte de testes automatizados com pytest
│   ├── test_schedule_extractor.py        # Validação do extrator de frequências e timetable do GTFS
│   ├── test_user_input_parser.py         # Testes de parse e reagrupamento de frequências do usuário
│   ├── test_comparison_engine.py         # Testes de matching 1:1 e faixas de resumo
│   ├── test_export_handler.py            # Testes de formatação, sanitização de nome e download de arquivos
│   └── test_ui_components.py             # Testes de validação de strings HTML limpas para a UI
├── requirements.txt                      # Declaração de dependências do Python
├── .gitignore                            # Arquivo de exclusão do controle de versão Git
├── README.md                             # Esta documentação rica e detalhada do sistema
└── analise-qh.Rproj                      # Configuração do projeto R
```

---

## 🛠️ Requisitos e Execução Local

### Dependências Necessárias
O aplicativo requer **Python 3.10 ou superior**. As dependências incluem:
* `streamlit` (Interface e fluxo reativo)
* `pandas` e `numpy` (Manipulação estruturada de dados)
* `gtfs-kit` (Análise específica de arquivos e feeds de trânsito GTFS)
* `pytest` (Ambiente e execução de testes automatizados)

### Passo a Passo de Execução

1. **Clone ou abra o repositório no diretório do projeto e instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Inicie a interface web do Streamlit:**
   ```bash
   python -m streamlit run app/main.py
   ```
   *O painel abrirá automaticamente no seu navegador padrão no endereço `http://localhost:8501`.*

3. **Execute os testes automatizados para validar a integridade da aplicação:**
   ```bash
   python -m pytest
   ```
   *Você verá a validação verde de todos os 24 testes passando com sucesso.*
