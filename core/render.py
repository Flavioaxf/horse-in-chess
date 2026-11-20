from __future__ import annotations

from collections.abc import Sequence

from core.tipos import Posicao, ResultadoExecucao


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
            navegação passo a passo na interface).

    Returns:
        Matriz ``n × n`` com inteiros ``1..k`` ou ``None``.
    """
    raise NotImplementedError("Implementar construir_matriz_visitas na feature F4 (render-cli).")


def formatar_tabuleiro_texto(
    n: int,
    percurso: Sequence[Posicao],
    passo_maximo: int | None = None,
) -> str:
    raise NotImplementedError("Implementar formatar_tabuleiro_texto na feature F4 (render-cli).")


def formatar_resumo_execucao(resultado: ResultadoExecucao) -> str:
    raise NotImplementedError("Implementar formatar_resumo_execucao na feature F4 (render-cli).")
