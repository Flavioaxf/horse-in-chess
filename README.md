# Passeio do Cavalo — Estratégia PARE

Trabalho Final T3 da disciplina **Complexidade de Algoritmos (2026.2)** — Universidade do Estado do Rio Grande do Norte (UERN), Profa. Rosiery Maia.

## Visão geral

Aplicação em Python 3.11+ para construção e análise de percursos abertos do cavalo (sem repetição de casas) em tabuleiros **5×5** e **8×8**, utilizando a estratégia **PARE (Preservação de Acessibilidade com Recuo Estratégico)** em:

- **2 modos:** `guloso` (sem recuo) e `recuo` (busca em profundidade com pilha explícita e orçamento `max_estados`);
- **2 variantes:** `restritiva` (principal, minimiza `(F, I, P, +A)`) e `expansiva` (comparação, minimiza `(F, I, P, -A)`).

> **Estado atual (F0 — contrato e esqueleto):** este repositório contém o contrato de dados (`core/tipos.py`), a estrutura de módulos com assinaturas (`NotImplementedError`), a configuração de testes e o fluxo inicial do projeto. As implementações das funcionalidades serão integradas via Pull Requests conforme o Gitflow da equipe.

## Estrutura do projeto

```text
.
├── app.py                   # Interface visual (Streamlit)
├── cli.py                   # Execução por linha de comando
├── core/
│   ├── tipos.py             # Contrato de dados compartilhado
│   ├── board.py             # Tabuleiro, movimentos do cavalo, adjacências e paridade
│   ├── pare.py              # Indicadores (F, I, P, A), ordenação e modo guloso
│   ├── busca.py             # Modo com recuo limitado (pilha explícita)
│   ├── metrics.py           # Contadores e cronômetro
│   ├── validator.py         # Validador independente de percursos
│   ├── render.py            # Renderização do tabuleiro numerado
│   └── api.py               # Ponto único de entrada: resolver(config)
├── experiments/             # Protocolo experimental e geração de CSV
├── results/                 # Resultados reproduzíveis (CSV)
└── tests/                   # Suíte de testes automatizados (pytest)
```

## Configuração do ambiente

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Comandos previstos

```bash
# Executar suíte de testes
pytest -q

# Execução via terminal (após implementação de F4/F6/F7)
python cli.py --n 8 --linha 1 --coluna 1 --modo recuo --variante restritiva --seed 2026 --max-estados 10000

# Interface visual (após implementação de F8)
streamlit run app.py

# Experimentos (após implementação de F9; CSV final gerado em release/1.0.0)
python experiments/run_experiments.py --saida results/experiments.csv
```

## Contribuição e Gitflow

- Branches principais: `main` (entregas com tag `vX.Y.Z`) e `develop` (integração via PR).
- Funcionalidades seguem `feature/<nome>` a partir de `develop`, integradas com *squash and merge*.
- Alterações no contrato (`core/tipos.py`) exigem PR próprio aprovado pelos três integrantes.
- Consulte as regras detalhadas de propriedade de arquivos, convenções de medição e critérios de aceitação no documento `AGENTS.md` da equipe.
