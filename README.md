# Passeio do Cavalo — Estratégia PARE

Trabalho Final T3 da disciplina **NCC0234 Complexidade de Algoritmos (2026.2)** — Universidade do Estado do Rio Grande do Norte (UERN), Profa. Rosiery Maia.

## Visão geral

Aplicação em Python 3.11+ que constrói percursos **abertos** do cavalo (sem repetir casas) em tabuleiros **5×5** e **8×8**, a partir de uma casa inicial escolhida pelo usuário, usando a estratégia **PARE (Preservação de Acessibilidade com Recuo Estratégico)**:

- **2 modos:** `guloso` (segue sempre o melhor candidato, sem voltar atrás) e `recuo` (busca em profundidade com pilha explícita e orçamento `max_estados`);
- **2 variantes:** `restritiva` (principal, minimiza `(F, I, P, +A)`) e `expansiva` (comparação, minimiza `(F, I, P, −A)`).

Para cada salto possível até uma casa `v`, o PARE olha o **grafo residual** (`v` mais as casas ainda livres) e ordena os candidatos lexicograficamente, sem pesos:

| Indicador | O que conta | Preferência |
|---|---|---|
| **F** — fragmentação | componentes conexas do grafo residual | menos |
| **I** — isolamento | casas livres sem vizinho livre | menos |
| **P** — pressão de extremidades | casas livres com um único vizinho livre | menos |
| **A** — acessibilidade | vizinhos livres de `v` | restritiva: menos; expansiva: mais |

A ordenação define **prioridade, não exclusão**: nenhum candidato é descartado por pontuação. Quando o passeio completo não é alcançado, o sistema devolve o **maior percurso encontrado dentro do orçamento** e informa o motivo da parada (`completo`, `sem_movimentos`, `busca_esgotada` ou `limite_estados`). Todo percurso passa por um **validador independente** antes de ser exibido.

## Instalação

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Dependências: `streamlit`, `pandas`, `matplotlib` (interface e gráficos) e `pytest` (testes). O núcleo (`core/`) usa só a biblioteca padrão.

## Como usar

### Interface visual

```bash
streamlit run app.py
```

Abre em `http://localhost:8501`. O fluxo é:

1. **Início** — apresentação do sistema; **Sobre o sistema** explica o problema, os indicadores e as métricas.
2. **Nova análise** — escolha do tabuleiro (5×5 ou 8×8), linha e coluna iniciais (1-based), modo, variante, orçamento `max_estados` (modo com recuo) e semente. Um tabuleiro de prévia mostra a casa inicial e os saltos possíveis.
3. **Percurso** — o cavalo percorre o melhor percurso encontrado, com animação; o botão *Pular para os resultados* vai direto à análise.
4. **Resultados** — tabuleiro numerado e navegável (súmula, setas do teclado, reprodução), eficácia (casas visitadas, cobertura, motivo da parada, aviso de paridade, conferência pelo validador) e eficiência (estados explorados, verificações de movimentos, avaliações de candidatos, recuos, tempo e verificações de preparo). O botão *Comparar as 4 combinações* roda os dois modos e as duas variantes na mesma casa inicial e semente.
5. **Experimentos** — gráficos e tabela lidos de `results/experiments.csv`. A interface não gera números próprios.

O menu lateral (seta no canto superior esquerdo) leva a qualquer tela. A cor do cavalo indica a região da casa inicial: branco nas linhas de cima, azul nas do meio e preto nas de baixo.

### Linha de comando

```bash
python cli.py --n 8 --linha 1 --coluna 1 --modo recuo --variante restritiva --seed 2026 --max-estados 10000
```

Coordenadas em 1-based. Sem `--modo`, usa `guloso`; no modo `recuo` sem `--max-estados`, usa 10000. A saída mostra o tabuleiro numerado pela ordem de visita e o resumo da execução. Use `python cli.py --help` para todas as opções.

### Experimentos

```bash
python experiments/run_experiments.py --saida results/experiments.csv
```

Executa o protocolo obrigatório — 4 cenários × 2 modos × 2 variantes = 16 execuções, com semente 2026 e `max_estados` 10000 por padrão (`--seed` e `--max-estados` alteram) — valida cada percurso e grava o CSV. Cenários:

| Cenário | Tabuleiro | Casa inicial (1-based) | Objetivo |
|---|---|---|---|
| T01 | 5×5 | (1, 1) | Canto |
| T02 | 5×5 | (1, 2) | Caso estruturalmente impossível (paridade) |
| T03 | 8×8 | (1, 1) | Canto |
| T04 | 8×8 | (4, 4) | Região central |

A coluna `versao_codigo` do CSV registra o commit que gerou os números. O arquivo em `results/` só é escrito por esse script.

### Testes

```bash
pytest -q
```

## Medição

| Métrica | Incrementa quando |
|---|---|
| `estados_explorados` | a busca entra em um caminho parcial válido (inclui a casa inicial) |
| `verificacoes_movimentos` | uma entrada de lista de adjacência é lida durante a resolução |
| `verificacoes_preparo` | um deslocamento é testado ao pré-calcular as adjacências (contado à parte) |
| `avaliacoes_candidatos` | a chave `(F, I, P, A)` de um candidato é calculada |
| `recuos` | uma casa é removida do caminho atual (sempre 0 no guloso) |
| `tempo_segundos` | `time.perf_counter()` em volta só da resolução |

Os contadores são incrementados durante a execução por `core/metrics.py`, nunca calculados por fórmula ao final.

## Estrutura do projeto

```text
.
├── app.py                   # Interface visual (Streamlit), em telas
├── componentes/tabuleiro/   # Componente do tabuleiro (prévia, animação e análise)
├── .streamlit/config.toml   # Tema da interface
├── cli.py                   # Execução por linha de comando
├── core/
│   ├── tipos.py             # Contrato de dados compartilhado
│   ├── board.py             # Tabuleiro, movimentos do cavalo, adjacências e paridade
│   ├── pare.py              # Indicadores (F, I, P, A), ordenação e modo guloso
│   ├── busca.py             # Modo com recuo limitado (pilha explícita)
│   ├── metrics.py           # Contadores e cronômetro
│   ├── validator.py         # Validador independente de percursos
│   ├── render.py            # Tabuleiro numerado em texto e resumo da execução
│   └── api.py               # Ponto único de entrada: resolver(config)
├── experiments/             # Cenários do protocolo e geração do CSV
├── results/                 # experiments.csv gerado pelo protocolo
└── tests/                   # Testes automatizados (pytest)
```

Toda execução passa por `core.api.resolver(config)`. O núcleo usa coordenadas 0-based; a conversão para 1-based acontece só na CLI, na interface e nos experimentos.

## Equipe e Gitflow

- Branches: `main` (entregas com tag `vX.Y.Z`), `develop` (integração por PR) e `feature/<nome>`.
- Commits no padrão Conventional Commits, em português.
- Regras de propriedade de arquivos, convenções de medição e critérios de aceitação estão no `AGENTS.md` da equipe.
