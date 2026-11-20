from __future__ import annotations

import random

from core.metrics import RegistradorMetricas
from core.tipos import (
    Adjacencias,
    AvaliacaoCandidato,
    MotivoParada,
    Posicao,
    VariantePARE,
)


def chave_ordenacao(
    avaliacao: AvaliacaoCandidato,
    variante: VariantePARE,
) -> tuple[int, int, int, int]:
    """Retorna a chave lexicográfica minimizada pela variante configurada.

    - ``"restritiva"``: ``(F, I, P, +A)``
    - ``"expansiva"``: ``(F, I, P, -A)``
    """
    raise NotImplementedError("Implementar chave_ordenacao na feature F5 (indicadores-pare).")


def avaliar_candidato(
    candidato: Posicao,
    visitadas: set[Posicao],
    adjacencias: Adjacencias,
    metricas: RegistradorMetricas,
) -> AvaliacaoCandidato:
    raise NotImplementedError("Implementar avaliar_candidato na feature F5 (indicadores-pare).")


def ordenar_candidatos(
    atual: Posicao,
    visitadas: set[Posicao],
    adjacencias: Adjacencias,
    variante: VariantePARE,
    rng: random.Random,
    metricas: RegistradorMetricas,
) -> list[AvaliacaoCandidato]:
    raise NotImplementedError("Implementar ordenar_candidatos na feature F5 (indicadores-pare).")


def executar_guloso(
    n: int,
    inicio: Posicao,
    variante: VariantePARE,
    adjacencias: Adjacencias,
    rng: random.Random,
    metricas: RegistradorMetricas,
) -> tuple[list[Posicao], MotivoParada]:
    """Executa a estratégia PARE no modo guloso (sem recuo; ``recuos == 0``).

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        inicio: Posição inicial em índices 0-based.
        variante: ``"restritiva"`` ou ``"expansiva"``.
        adjacencias: Mapa pré-calculado de vizinhos válidos.
        rng: Gerador pseudoaleatório local (``random.Random(seed)``).
        metricas: Registrador centralizado de métricas da execução.

    Returns:
        Tupla ``(caminho, motivo_parada)``, com ``motivo_parada`` em
        ``{"completo", "sem_movimentos"}``.
    """
    raise NotImplementedError("Implementar executar_guloso na feature F6 (modo-guloso).")
