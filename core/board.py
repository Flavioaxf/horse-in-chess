from __future__ import annotations

from collections.abc import Callable

from core.tipos import Adjacencias, DIMENSOES_OBRIGATORIAS, Posicao

KNIGHT_MOVES: tuple[tuple[int, int], ...] = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)

def validar_dimensao(
    n: int,
    permitidas: tuple[int, ...] = DIMENSOES_OBRIGATORIAS,
) -> None:
    """Valida se a dimensão ``n`` do tabuleiro é aceita.

    Args:
        n: Dimensão do tabuleiro quadrado ``n × n``.
        permitidas: Tupla de dimensões aceitas (por padrão ``(5, 8)``).

    Raises:
        ValueError: Se ``n`` não for um inteiro válido ou não estiver em ``permitidas``.
    """
    raise NotImplementedError("Implementar validar_dimensao na feature F1 (grafo-movimentos).")


def dentro_do_tabuleiro(n: int, linha: int, coluna: int) -> bool:
    raise NotImplementedError("Implementar dentro_do_tabuleiro na feature F1 (grafo-movimentos).")


def validar_posicao(n: int, posicao: Posicao) -> None:
    """Valida se ``posicao`` está dentro dos limites do tabuleiro ``n × n``.

    Raises:
        ValueError: Se ``posicao`` estiver fora do tabuleiro ou em formato inválido.
    """
    raise NotImplementedError("Implementar validar_posicao na feature F1 (grafo-movimentos).")


def eh_salto_valido(origem: Posicao, destino: Posicao) -> bool:
    raise NotImplementedError("Implementar eh_salto_valido na feature F1 (grafo-movimentos).")


def gerar_adjacencias(
    n: int,
    ao_verificar_preparo: Callable[[], None] | None = None,
) -> Adjacencias:
    """Pré-calcula as listas de vizinhos válidos para todas as casas do tabuleiro ``n × n``.

    Cada deslocamento de ``KNIGHT_MOVES`` testado contra os limites do tabuleiro
    deve acionar ``ao_verificar_preparo()`` quando o callback for fornecido,
    permitindo registrar ``verificacoes_preparo`` exclusivamente via ``core/metrics.py``.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        ao_verificar_preparo: Callback opcional chamado a cada teste de deslocamento.

    Returns:
        Dicionário mapeando cada casa ``(linha, coluna)`` para sua tupla de vizinhos válidos.
    """
    raise NotImplementedError("Implementar gerar_adjacencias na feature F1 (grafo-movimentos).")


def cor_casa(posicao: Posicao) -> int:
    """Retorna a paridade de cor da casa (``0`` ou ``1``) via ``(linha + coluna) % 2``."""
    raise NotImplementedError("Implementar cor_casa na feature F1 (grafo-movimentos).")


def verificar_impossibilidade_paridade(n: int, inicio: Posicao) -> bool:
    """Detecta se o passeio completo é estruturalmente impossível por paridade de cor.

    Em tabuleiros quadrados de dimensão ímpar (como 5×5), existem mais casas
    com ``(linha + coluna) % 2 == 0`` (cor majoritária) do que com resto 1
    (cor minoritária). Um passeio completo alterna cores a cada salto e,
    portanto, só pode existir se iniciar na cor majoritária.

    Este detector é apenas informativo: nunca altera o ponto de partida nem
    interrompe a busca pelo maior percurso parcial.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        inicio: Posição inicial em índices 0-based.

    Returns:
        ``True`` quando a impossibilidade por paridade é demonstrável; ``False`` caso contrário.
    """
    raise NotImplementedError(
        "Implementar verificar_impossibilidade_paridade na feature F1 (grafo-movimentos)."
    )
