# Base de Conhecimento a partir de Manual Técnico: Volkswagen Nivus

Repositório oficial do trabalho prático da disciplina **Extração e Preparação de Dados (AP2)**, sob a supervisão do Professor Alvaro Riz de Barros. O projeto consiste na transformação do manual técnico original do **Volkswagen Nivus** (código editorial `21B.5B1.NIV.66`) em uma base de conhecimento textual estruturada, limpa e preparada para consumo por sistemas de Inteligência Artificial (geração de *embeddings*, bancos de dados vetoriais, pipelines RAG, Google Gemini Gems e OpenAI Custom GPTs).

## 📁 Estrutura do Repositório

```
.
├── base_conhecimento_nivus/         # Entregável 2: Chunks organizados por capítulo (27 pastas)
│   ├── 00_garantia_e_plano_digital/
│   ├── 01_sobre_o_manual/
│   ├── ...
│   └── 26_abreviaturas_e_indice_remissivo/
├── pipeline_chunking.py                # Entregável 1: Script principal do pipeline de extração e chunking (v5)
├── Relatório Técnico - Base de Conhecimento VW Nivus # Entregável 3: Documentação do processo e relatório técnico
├── auditar_chunks.py                # Script automatizado de auditoria e controle de qualidade
├── relatorio_metricas.json          # Métricas quantitativas consolidadas da base
├── relatorio_auditoria.txt          # Relatório gerado pela auditoria de integridade
└── README.md                        # Documentação descritiva do projeto

```

## 🚀 Visão Geral da Arquitetura do Pipeline

O processo foi desenvolvido em Python utilizando a biblioteca `PyMuPDF` (`fitz`) e estruturado em quatro etapas principais:

1. **Extração Espacial e Tipográfica:**

   * Leitura de baixo nível do PDF (309 páginas).

   * Divisão geométrica do miolo em duas colunas paralelas (`x < largura / 2` e `x >= largura / 2`) para preservar a ordem correta de leitura e evitar cruzamento de linhas.

   * Extração de tabelas estruturadas por recorte geométrico de células (`clip=cell_rect`), garantindo o isolamento correto de vírgulas decimais, unidades e separadores em Markdown (`| --- |`).

2. **Preparação e Higienização Semântica:**

   * Remoção automática de cabeçalhos (código `21B.5B1.NIV.66`) e rodapés repetitivos (`N Manual de instruções`).

   * Limpeza de glifos proprietários da fonte Volkswagen (área PUA Unicode).

   * Normalização de alertas críticos de segurança (`PERIGO`, `ATENÇÃO`, `CUIDADO`, `NOTA`) em tags padronizadas (`[PERIGO]`, `[ATENÇÃO]`, `[CUIDADO]`, `[NOTA]`).

   * Recomposição seletiva de palavras hifenizadas e fusão de prosa partida entre colunas ou páginas.

3. **Chunking Híbrido (Estrutural + Janela Semântica com Overlap):**

   * Divisão guiada pela macroestrutura oficial do manual (26 capítulos + preliminares).

   * Restrição de tamanho máximo de fragmento (`2.400 caracteres`) e fusão de caudas residuais curtas (`< 220 caracteres`).

   * Aplicação de **sobreposição contextual (*overlap*)** condicional intrasseção para garantir continuidade semântica entre partes consecutivas de procedimentos longos.

4. **Enriquecimento com Metadados e Rastreabilidade:**

   * Inserção de um cabeçalho estruturado em 100% dos arquivos `.txt`, contendo código do documento, capítulo, seção, páginas de referência (manual e PDF), figuras citadas (`Fig. X`), alertas presentes, presença de tabela e dependência visual.

## 📊 Estatísticas Consolidadas da Base (Métricas Finais)

* **Total de Arquivos Gerados (*Chunks*):** 414 arquivos `.txt` (codificação `UTF-8`)

* **Total de Pastas Temáticas:** 27 diretórios (espelhando a árvore do manual)

* **Tamanho Médio por Chunk:** 2.049,6 caracteres (\~450 a 520 tokens)

* **Chunks com Alertas de Segurança:** 216 arquivos (52,2%)

* **Chunks com Tabelas Estruturadas:** 38 arquivos (9,2%)

* **Chunks com Dependência Visual (`Fig.`):** 184 arquivos (44,4%)

## 🛠️ Como Executar o Projeto

### Pré-requisitos

Certifique-se de ter o Python 3.8+ instalado e a biblioteca `PyMuPDF` configurada no ambiente:

```
pip install pymupdf

```

### 1. Gerar a Base de Conhecimento (Entregável 2)

Coloque o script `pipeline_nivus.py` na mesma pasta onde está o arquivo PDF original (`Manual de instruções - NIVUS.pdf`) e execute:

```
python pipeline_nivus.py

```

Isso criará a pasta `base_conhecimento_nivus/` com os 414 chunks organizados e atualizará o arquivo `relatorio_metricas.json`.

### 2. Auditar a Qualidade dos Chunks (Controle de Qualidade)

Para verificar a integridade estrutural, ausência de quebras de prosa e alinhamento de tabelas em toda a base gerada, execute o script de auditoria:

```
python auditar_chunks.py

```

O script gera o arquivo `relatorio_auditoria.txt` atestando os indicadores de conformidade (0% de erros de metadados, 0% de tabelas desalinhadas e 0% de glifos residuais).

## 📦 Entregáveis da Atividade (AP2)

O trabalho está estruturado para entrega em formato de pacote compactado (`.zip`), contendo:

1. **Entregável 1:** Script de automação (`pipeline_nivus.py`), script de auditoria (`auditar_chunks.py`) e métricas (`relatorio_metricas.json`).

2. **Entregável 2:** A árvore completa de diretórios em `base_conhecimento_nivus/` com os 414 fragmentos textuais.

3. **Entregável 3:** Relatório Técnico detalhado em formato PDF, estruturado nos 7 tópicos exigidos pela disciplina.
