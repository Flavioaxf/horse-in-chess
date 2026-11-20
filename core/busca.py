from __future__ import annotations

import random

from core.metrics import RegistradorMetricas
from core.pare import ordenar_candidatos  # noqa: F401
from core.tipos import Adjacencias, MotivoParada, Posicao, VariantePARE


def executar_recuo(
    n: int,
    inicio: Posicao,
    variante: VariantePARE,
    max_estados: int,
    adjacencias: Adjacencias,
    rng: random.Random,
    metricas: RegistradorMetricas,
    podar_inviaveis: bool = False,
) -> tuple[list[Posicao], MotivoParada]:
    """Executa a estratégia PARE no modo com recuo limitado por ``max_estados``.

    Args:
        n: Dimensão do tabuleiro ``n × n``.
        inicio: Posição inicial em índices 0-based.
        variante: ``"restritiva"`` ou ``"expansiva"``.
        max_estados: Orçamento máximo de estados explorados (deve ser ``>= 1``).
        adjacencias: Mapa pré-calculado de vizinhos válidos.
        rng: Gerador pseudoaleatório local (``random.Random(seed)``).
        metricas: Registrador centralizado de métricas da execução.
        podar_inviaveis: Se ``True``, descarta candidatos com ``completo_ainda_possivel == False``;
            obrigatório ser ``False`` por padrão.

    Returns:
        Tupla ``(melhor_caminho, motivo_parada)``, com ``motivo_parada`` em
        ``{"completo", "busca_esgotada", "limite_estados"}``.
    """
    raise NotImplementedError("Implementar executar_recuo na feature F7 (modo-recuo).")
