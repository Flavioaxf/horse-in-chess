from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.tipos import ConfiguracaoExecucao, ModoExecucao, VariantePARE

SEED_PADRAO: int = 2026
MAX_ESTADOS_PADRAO: int = 10_000

MODOS_PROTOCOLO: tuple[ModoExecucao, ...] = ("guloso", "recuo")
VARIANTES_PROTOCOLO: tuple[VariantePARE, ...] = ("restritiva", "expansiva")


@dataclass(frozen=True)
class CenarioExperimental:
    codigo: str
    n: int
    linha_1based: int
    coluna_1based: int
    objetivo: str


CENARIOS_OBRIGATORIOS: tuple[CenarioExperimental, ...] = (
    CenarioExperimental("T01", 5, 1, 1, "Canto"),
    CenarioExperimental("T02", 5, 1, 2, "Caso estruturalmente impossível (paridade)"),
    CenarioExperimental("T03", 8, 1, 1, "Canto"),
    CenarioExperimental("T04", 8, 4, 4, "Região central"),
)


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def gerar_configuracoes_protocolo(
    seed: int = SEED_PADRAO,
    max_estados: int = MAX_ESTADOS_PADRAO,
    cenarios: Sequence[CenarioExperimental] = CENARIOS_OBRIGATORIOS,
) -> list[tuple[CenarioExperimental, ConfiguracaoExecucao]]:
    """Gera as combinações do protocolo experimental (cenários × modos × variantes).

    Args:
        seed: Semente inteira determinística compartilhada entre execuções.
        max_estados: Orçamento máximo de estados para o modo ``recuo`` (``>= 1``).
        cenarios: Sequência de cenários experimentais em coordenadas 1-based.

    Returns:
        Lista ordenada de pares ``(cenario, config)``.

    Raises:
        ValueError: Se ``seed``, ``max_estados`` ou alguma coordenada de cenário
            for inválida.
    """
    if not _eh_inteiro_estrito(seed):
        raise ValueError(
            f"Semente inválida: esperado inteiro, recebido {type(seed).__name__} ({seed!r})."
        )
    if not _eh_inteiro_estrito(max_estados) or max_estados < 1:
        raise ValueError(
            f"Orçamento max_estados inválido: esperado inteiro >= 1, recebido {max_estados!r}."
        )

    configuracoes: list[tuple[CenarioExperimental, ConfiguracaoExecucao]] = []
    for cenario in cenarios:
        if not (1 <= cenario.linha_1based <= cenario.n and 1 <= cenario.coluna_1based <= cenario.n):
            raise ValueError(
                f"Cenário {cenario.codigo}: posição 1-based "
                f"({cenario.linha_1based}, {cenario.coluna_1based}) fora do tabuleiro "
                f"{cenario.n}×{cenario.n}."
            )

        inicio_0based = (cenario.linha_1based - 1, cenario.coluna_1based - 1)
        for modo in MODOS_PROTOCOLO:
            for variante in VARIANTES_PROTOCOLO:
                config = ConfiguracaoExecucao(
                    n=cenario.n,
                    inicio=inicio_0based,
                    modo=modo,
                    variante=variante,
                    seed=seed,
                    max_estados=max_estados if modo == "recuo" else None,
                )
                configuracoes.append((cenario, config))

    return configuracoes
