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

_KNIGHT_MOVES_SET: frozenset[tuple[int, int]] = frozenset(KNIGHT_MOVES)


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_formato_posicao(posicao: Posicao) -> tuple[int, int]:
    if not isinstance(posicao, tuple) or len(posicao) != 2:
        raise ValueError(
            f"Posição inválida: esperado tupla (linha, coluna), recebido {posicao!r}."
        )
    linha, coluna = posicao
    if not (_eh_inteiro_estrito(linha) and _eh_inteiro_estrito(coluna)):
        raise ValueError(
            f"Posição inválida: coordenadas devem ser inteiros, recebido {posicao!r}."
        )
    return linha, coluna


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
    if not _eh_inteiro_estrito(n):
        raise ValueError(
            f"Dimensão inválida: esperado inteiro, recebido {type(n).__name__} ({n!r})."
        )
    if n <= 0 or n not in permitidas:
        raise ValueError(
            f"Dimensão {n} não suportada. Dimensões aceitas: {permitidas}."
        )


def dentro_do_tabuleiro(n: int, linha: int, coluna: int) -> bool:
    """Retorna ``True`` se ``(linha, coluna)`` estiver dentro de um tabuleiro ``n × n``."""
    if not (
        _eh_inteiro_estrito(n)
        and _eh_inteiro_estrito(linha)
        and _eh_inteiro_estrito(coluna)
    ):
        return False
    return n > 0 and 0 <= linha < n and 0 <= coluna < n


def validar_posicao(n: int, posicao: Posicao) -> None:
    """Valida se ``posicao`` está dentro dos limites do tabuleiro ``n × n``.

    Raises:
        ValueError: Se ``n`` não for inteiro positivo ou se ``posicao`` estiver
            fora do tabuleiro ou em formato inválido.
    """
    if not _eh_inteiro_estrito(n) or n <= 0:
        raise ValueError(
            f"Dimensão inválida para validação de posição: esperado inteiro positivo, recebido {n!r}."
        )
    linha, coluna = _validar_formato_posicao(posicao)
    if not dentro_do_tabuleiro(n, linha, coluna):
        raise ValueError(
            f"Posição {posicao} fora dos limites do tabuleiro {n}×{n} (esperado 0..{n - 1})."
        )


def eh_salto_valido(origem: Posicao, destino: Posicao) -> bool:
    if (
        not isinstance(origem, tuple)
        or len(origem) != 2
        or not isinstance(destino, tuple)
        or len(destino) != 2
    ):
        return False
    linha_origem, coluna_origem = origem
    linha_destino, coluna_destino = destino
    if not (
        _eh_inteiro_estrito(linha_origem)
        and _eh_inteiro_estrito(coluna_origem)
        and _eh_inteiro_estrito(linha_destino)
        and _eh_inteiro_estrito(coluna_destino)
    ):
        return False
    return (linha_destino - linha_origem, coluna_destino - coluna_origem) in _KNIGHT_MOVES_SET


def gerar_adjacencias(
    n: int,
    ao_verificar_preparo: Callable[[], None] | None = None,
) -> Adjacencias:
    """Pré-calcula as listas de vizinhos válidos para todas as casas do tabuleiro ``n × n``.

    Cada deslocamento de ``KNIGHT_MOVES`` testado contra os limites do tabuleiro
    aciona ``ao_verificar_preparo()`` quando o callback é fornecido, permitindo
    registrar ``verificacoes_preparo`` exclusivamente via ``core/metrics.py``.

    Args:
        n: Dimensão do tabuleiro ``n × n`` (inteiro positivo).
        ao_verificar_preparo: Callback opcional chamado a cada teste de deslocamento.

    Returns:
        Dicionário mapeando cada casa ``(linha, coluna)`` para sua tupla de vizinhos válidos.

    Raises:
        ValueError: Se ``n`` não for um inteiro positivo.
    """
    if not _eh_inteiro_estrito(n) or n <= 0:
        raise ValueError(
            f"Dimensão inválida para geração de adjacências: esperado inteiro positivo, recebido {n!r}."
        )

    adjacencias: Adjacencias = {}
    for linha in range(n):
        for coluna in range(n):
            vizinhos: list[Posicao] = []
            for dl, dc in KNIGHT_MOVES:
                if ao_verificar_preparo is not None:
                    ao_verificar_preparo()
                nova_linha = linha + dl
                nova_coluna = coluna + dc
                if dentro_do_tabuleiro(n, nova_linha, nova_coluna):
                    vizinhos.append((nova_linha, nova_coluna))
            adjacencias[(linha, coluna)] = tuple(vizinhos)
    return adjacencias


def cor_casa(posicao: Posicao) -> int:
    linha, coluna = _validar_formato_posicao(posicao)
    return (linha + coluna) % 2


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
    validar_posicao(n, inicio)
    return (n % 2 == 1) and (cor_casa(inicio) == 1)
