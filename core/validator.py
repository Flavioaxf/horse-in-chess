from __future__ import annotations

from collections.abc import Sequence

from core.board import KNIGHT_MOVES, dentro_do_tabuleiro, eh_salto_valido  # noqa: F401
from core.tipos import Posicao, ResultadoValidacao


def validar_percurso(
    n: int,
    inicio: Posicao,
    percurso: Sequence[Posicao],
) -> ResultadoValidacao:
    """Valida de forma independente um percurso aberto do cavalo.

    Deve verificar:
    1. Dimensão ``n`` válida (positiva; conforme regras do tabuleiro).
    2. Percurso não vazio e iniciado exatamente em ``inicio``.
    3. Todas as posições dentro dos limites ``0 <= linha, coluna < n``.
    4. Ausência de casas repetidas no percurso.
    5. Todos os pares consecutivos formam saltos válidos em ``KNIGHT_MOVES``.
    6. ``passeio_completo`` verdadeiro somente se ``valido`` e ``len(percurso) == n * n``.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        inicio: Posição inicial esperada (0-based).
        percurso: Sequência ordenada de casas visitadas (0-based).

    Returns:
        ``ResultadoValidacao`` indicando validade, completude e eventuais erros.
    """
    raise NotImplementedError("Implementar validar_percurso na feature F3 (validador).")
