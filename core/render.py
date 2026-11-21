"""Renderização textual do tabuleiro numerado e do resumo de uma execução.

Este módulo depende **somente** de ``core.tipos``: não conhece o algoritmo,
apenas desenha o ``melhor_percurso`` recebido. As coordenadas internas são
0-based; os rótulos dos eixos exibidos ao usuário são 1-based.
"""

from __future__ import annotations

from collections.abc import Sequence

from core.tipos import MotivoParada, Posicao, ResultadoExecucao

MARCADOR_NAO_VISITADA = "-"

DESCRICAO_MOTIVO: dict[str, str] = {
    "completo": "passeio completo encontrado",
    "sem_movimentos": (
        "esgotamento da estratégia: modo guloso sem movimentos válidos a partir da última casa"
    ),
    "busca_esgotada": (
        "esgotamento da estratégia: todas as alternativas foram exploradas dentro do orçamento"
    ),
    "limite_estados": "limite de execução: orçamento max_estados atingido",
}


def _validar_n(n: int) -> None:
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError(f"Dimensão inválida para renderização: {n!r}.")


def _resolver_passo_maximo(total: int, passo_maximo: int | None) -> int:
    if passo_maximo is None:
        return total
    if not isinstance(passo_maximo, int) or isinstance(passo_maximo, bool) or passo_maximo < 0:
        raise ValueError(f"passo_maximo inválido: {passo_maximo!r}.")
    return min(passo_maximo, total)


def construir_matriz_visitas(
    n: int,
    percurso: Sequence[Posicao],
    passo_maximo: int | None = None,
) -> list[list[int | None]]:
    """Constrói a matriz ``n × n`` numerada de ``1..k`` nas casas visitadas.

    Casas não visitadas (ou além de ``passo_maximo``) recebem ``None``.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        percurso: Sequência ordenada de casas visitadas (0-based).
        passo_maximo: Quantidade opcional de passos iniciais a exibir (útil para
            navegação passo a passo na interface). Valores maiores que o
            percurso são limitados ao seu comprimento.

    Returns:
        Matriz ``n × n`` com inteiros ``1..k`` ou ``None``.

    Raises:
        ValueError: Se ``n`` ou ``passo_maximo`` forem inválidos, se alguma casa
            estiver fora do tabuleiro ou se houver casa repetida no percurso.
    """
    _validar_n(n)
    k = _resolver_passo_maximo(len(percurso), passo_maximo)

    matriz: list[list[int | None]] = [[None] * n for _ in range(n)]
    for ordem, (linha, coluna) in enumerate(percurso[:k], start=1):
        if not (0 <= linha < n and 0 <= coluna < n):
            raise ValueError(
                f"Casa {(linha, coluna)} (passo {ordem}) fora do tabuleiro {n}×{n}."
            )
        if matriz[linha][coluna] is not None:
            raise ValueError(
                f"Casa {(linha, coluna)} repetida no percurso (passos "
                f"{matriz[linha][coluna]} e {ordem})."
            )
        matriz[linha][coluna] = ordem
    return matriz


def formatar_tabuleiro_texto(
    n: int,
    percurso: Sequence[Posicao],
    passo_maximo: int | None = None,
) -> str:
    """Desenha o tabuleiro numerado pela ordem de visita, em texto monoespaçado.

    Linhas e colunas são rotuladas de ``1`` a ``n``; casas não visitadas
    aparecem como ``-``.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        percurso: Sequência ordenada de casas visitadas (0-based).
        passo_maximo: Quantidade opcional de passos iniciais a exibir.

    Returns:
        Texto com ``n + 1`` linhas (cabeçalho de colunas + uma linha por fileira).
    """
    matriz = construir_matriz_visitas(n, percurso, passo_maximo)
    largura = max(len(str(n * n)), len(str(n)))
    largura_rotulo = len(str(n))

    cabecalho = " " * largura_rotulo + " |" + "".join(
        f" {coluna:>{largura}}" for coluna in range(1, n + 1)
    )
    separador = "-" * largura_rotulo + "-+" + "-" * ((largura + 1) * n)

    linhas = [cabecalho, separador]
    for indice, fileira in enumerate(matriz, start=1):
        celulas = "".join(
            f" {(MARCADOR_NAO_VISITADA if valor is None else valor):>{largura}}"
            for valor in fileira
        )
        linhas.append(f"{indice:>{largura_rotulo}} |{celulas}")
    return "\n".join(linhas)


def descrever_motivo_parada(motivo: MotivoParada) -> str:
    """Retorna a explicação textual de ``motivo_parada`` exibida ao usuário."""
    try:
        return DESCRICAO_MOTIVO[motivo]
    except KeyError as erro:
        raise ValueError(f"Motivo de parada desconhecido: {motivo!r}.") from erro


def formatar_resumo_execucao(resultado: ResultadoExecucao) -> str:
    """Formata as métricas de eficácia e eficiência de uma execução.

    Todos os números vêm diretamente de ``resultado``; nada é estimado aqui.
    A posição inicial não é impressa neste módulo (a conversão para 1-based é
    responsabilidade de ``cli.py``/``app.py``).

    Args:
        resultado: Resultado devolvido por ``core.api.resolver``.

    Returns:
        Texto com várias linhas, separado em blocos de configuração, eficácia e
        eficiência.
    """
    cfg = resultado.config
    orcamento = "não se aplica" if cfg.max_estados is None else str(cfg.max_estados)
    concluido = "sim" if resultado.passeio_completo else "não"

    linhas = [
        "Configuração",
        f"  modo .................... {cfg.modo}",
        f"  variante ................ {cfg.variante}",
        f"  semente utilizada ....... {resultado.seed_utilizada}",
        f"  orçamento (max_estados) . {orcamento}",
        f"  versão do código ........ {resultado.versao_codigo}",
        "",
        "Eficácia",
        f"  casas visitadas ......... {resultado.casas_visitadas} de {resultado.total_casas}",
        f"  cobertura ............... {resultado.cobertura_percentual:.2f}%",
        f"  passeio completo ........ {concluido}",
        f"  motivo de parada ........ {resultado.motivo_parada} "
        f"({descrever_motivo_parada(resultado.motivo_parada)})",
        "",
        "Eficiência",
        f"  tempo de resolução ...... {resultado.tempo_segundos:.6f} s",
        f"  estados explorados ...... {resultado.estados_explorados}",
        f"  verificações de movim. .. {resultado.verificacoes_movimentos}",
        f"  verificações de preparo . {resultado.verificacoes_preparo}",
        f"  avaliações de candidatos  {resultado.avaliacoes_candidatos}",
        f"  recuos .................. {resultado.recuos}",
        "",
        "Métrica de esforço: 'verificações de movim.' soma cada entrada lida de uma",
        "lista de adjacência durante a resolução (candidatos, graus e BFS/DFS do grafo",
        "residual). O pré-cálculo das adjacências é contado à parte em 'preparo'.",
        "Estados = entradas em caminhos parciais válidos (inclui a casa inicial).",
    ]

    if resultado.impossibilidade_paridade:
        linhas += [
            "",
            "Aviso de paridade: a casa inicial é da cor minoritária de um tabuleiro de",
            "dimensão ímpar; um passeio completo é estruturalmente impossível e o",
            f"máximo teórico é {resultado.total_casas - 1} casas. A busca não foi alterada.",
        ]
    return "\n".join(linhas)
