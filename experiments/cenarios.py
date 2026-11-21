from __future__ import annotations

from dataclasses import dataclass

from core.tipos import ConfiguracaoExecucao


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


def gerar_configuracoes_protocolo(
    seed: int = 2026,
    max_estados: int = 10_000,
) -> list[tuple[CenarioExperimental, ConfiguracaoExecucao]]:
    raise NotImplementedError(
        "Implementar gerar_configuracoes_protocolo na feature F9 (experimentos)."
    )
