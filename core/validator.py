from __future__ import annotations

from collections.abc import Sequence

from core.board import dentro_do_tabuleiro, eh_salto_valido
from core.tipos import Posicao, ResultadoValidacao


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _eh_posicao_valida(posicao: object) -> bool:
    return (
        isinstance(posicao, tuple)
        and len(posicao) == 2
        and _eh_inteiro_estrito(posicao[0])
        and _eh_inteiro_estrito(posicao[1])
    )


def validar_percurso(
    n: int,
    inicio: Posicao,
    percurso: Sequence[Posicao],
) -> ResultadoValidacao:
    """Valida de forma independente um percurso aberto do cavalo.

    Verifica, sem depender dos módulos da estratégia PARE ou de busca:
    1. Dimensão ``n`` válida (inteiro positivo).
    2. Posição ``inicio`` válida e dentro do tabuleiro ``n × n``.
    3. Percurso como sequência ordenada não vazia, iniciada exatamente em ``inicio``.
    4. Todas as posições em formato ``(linha, coluna)`` de inteiros e dentro dos
       limites ``0 <= linha, coluna < n``.
    5. Ausência de casas repetidas no percurso.
    6. Todos os pares consecutivos formam saltos válidos em ``KNIGHT_MOVES``.
    7. ``passeio_completo`` verdadeiro somente se ``valido`` e todas as ``n * n``
       casas distintas do tabuleiro forem visitadas (passeio aberto).

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        inicio: Posição inicial esperada (0-based).
        percurso: Sequência ordenada de casas visitadas (0-based).

    Returns:
        ``ResultadoValidacao`` indicando validade, completude e eventuais erros.
    """
    erros: list[str] = []

    n_valido = _eh_inteiro_estrito(n) and n > 0
    if not n_valido:
        erros.append(
            f"Dimensão inválida: esperado inteiro positivo, recebido {type(n).__name__} ({n!r})."
        )

    inicio_formato_valido = _eh_posicao_valida(inicio)
    if not inicio_formato_valido:
        erros.append(
            "Posição inicial inválida: esperado tupla (linha, coluna) de inteiros, "
            f"recebido {inicio!r}."
        )
    elif n_valido and not dentro_do_tabuleiro(n, inicio[0], inicio[1]):
        erros.append(
            f"Posição inicial {inicio} fora dos limites do tabuleiro {n}×{n}."
        )

    if not isinstance(percurso, Sequence) or isinstance(
        percurso, (str, bytes, bytearray)
    ):
        erros.append(
            "Percurso inválido: esperado sequência ordenada de posições, "
            f"recebido {type(percurso).__name__}."
        )
        return ResultadoValidacao(
            valido=False,
            passeio_completo=False,
            erros=tuple(erros),
        )

    if len(percurso) == 0:
        erros.append("Percurso vazio: deve conter ao menos a posição inicial.")
        return ResultadoValidacao(
            valido=False,
            passeio_completo=False,
            erros=tuple(erros),
        )

    vistas: dict[Posicao, int] = {}
    anterior: Posicao | None = None
    anterior_valido = False

    for indice, posicao in enumerate(percurso):
        if not _eh_posicao_valida(posicao):
            erros.append(
                f"Posição inválida no índice {indice}: esperado tupla (linha, coluna) "
                f"de inteiros, recebido {posicao!r}."
            )
            anterior = None
            anterior_valido = False
            continue

        if indice == 0 and inicio_formato_valido and posicao != inicio:
            erros.append(
                f"Percurso deve iniciar em {inicio}, mas iniciou em {posicao}."
            )

        if n_valido and not dentro_do_tabuleiro(n, posicao[0], posicao[1]):
            erros.append(
                f"Posição {posicao} no índice {indice} está fora dos limites do tabuleiro {n}×{n}."
            )

        if posicao in vistas:
            erros.append(
                f"Casa repetida {posicao} no índice {indice} "
                f"(já visitada no índice {vistas[posicao]})."
            )
        else:
            vistas[posicao] = indice

        if indice > 0 and anterior_valido and anterior is not None:
            if not eh_salto_valido(anterior, posicao):
                erros.append(
                    f"Salto inválido do índice {indice - 1} {anterior} "
                    f"para o índice {indice} {posicao}."
                )

        anterior = posicao
        anterior_valido = True

    valido = len(erros) == 0
    passeio_completo = (
        valido and n_valido and len(percurso) == n * n and len(vistas) == n * n
    )
    return ResultadoValidacao(
        valido=valido,
        passeio_completo=passeio_completo,
        erros=tuple(erros),
    )
