from __future__ import annotations

from dataclasses import dataclass
import random

from core.metrics import RegistradorMetricas
from core.pare import ordenar_candidatos
from core.tipos import (
    Adjacencias,
    AvaliacaoCandidato,
    MotivoParada,
    Posicao,
    VARIANTES_VALIDAS,
    VariantePARE,
)


@dataclass
class _QuadroBusca:
    candidatos: list[AvaliacaoCandidato]
    proximo_indice: int = 0


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _obter_candidatos(
    atual: Posicao,
    visitadas: set[Posicao],
    adjacencias: Adjacencias,
    variante: VariantePARE,
    rng: random.Random,
    metricas: RegistradorMetricas,
    podar_inviaveis: bool,
) -> list[AvaliacaoCandidato]:
    candidatos = ordenar_candidatos(
        atual=atual,
        visitadas=visitadas,
        adjacencias=adjacencias,
        variante=variante,
        rng=rng,
        metricas=metricas,
    )
    if podar_inviaveis:
        return [
            avaliacao
            for avaliacao in candidatos
            if avaliacao.completo_ainda_possivel
        ]
    return candidatos


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
        podar_inviaveis: Se ``True``, descarta candidatos com
            ``completo_ainda_possivel == False``; obrigatório ser ``False``
            por padrão (Proposição 5.3 usada apenas como sinalizador).

    Returns:
        Tupla ``(melhor_caminho, motivo_parada)``, com ``motivo_parada`` em
        ``{"completo", "busca_esgotada", "limite_estados"}``.

    Raises:
        ValueError: Se algum parâmetro de entrada for inválido ou incompatível
            com o mapa de adjacências.
    """
    if not _eh_inteiro_estrito(n) or n <= 0:
        raise ValueError(
            "Dimensão inválida no modo com recuo: esperado inteiro positivo, "
            f"recebido {n!r}."
        )
    if variante not in VARIANTES_VALIDAS:
        raise ValueError(
            f"Variante PARE inválida: {variante!r}. "
            f"Valores aceitos: {sorted(VARIANTES_VALIDAS)}."
        )
    if not _eh_inteiro_estrito(max_estados) or max_estados < 1:
        raise ValueError(
            "Orçamento max_estados inválido: esperado inteiro >= 1, "
            f"recebido {max_estados!r}."
        )
    if not isinstance(podar_inviaveis, bool):
        raise ValueError(
            "Parâmetro podar_inviaveis inválido: esperado bool, "
            f"recebido {type(podar_inviaveis).__name__}."
        )

    total_casas = n * n
    if len(adjacencias) != total_casas:
        raise ValueError(
            f"Mapa de adjacências incompatível com tabuleiro {n}×{n}: "
            f"esperado {total_casas} casas, recebido {len(adjacencias)}."
        )
    if inicio not in adjacencias:
        raise ValueError(
            f"Posição inicial inválida: {inicio!r} não pertence ao mapa de adjacências."
        )

    caminho_atual: list[Posicao] = [inicio]
    visitadas: set[Posicao] = {inicio}
    melhor_caminho: list[Posicao] = [inicio]

    metricas.registrar_estado()
    estados_nesta_busca = 1

    if total_casas == 1:
        return melhor_caminho, "completo"

    if estados_nesta_busca >= max_estados:
        return melhor_caminho, "limite_estados"

    candidatos_raiz = _obter_candidatos(
        atual=inicio,
        visitadas=visitadas,
        adjacencias=adjacencias,
        variante=variante,
        rng=rng,
        metricas=metricas,
        podar_inviaveis=podar_inviaveis,
    )
    pilha: list[_QuadroBusca] = [_QuadroBusca(candidatos=candidatos_raiz)]

    while pilha:
        topo = pilha[-1]

        if topo.proximo_indice < len(topo.candidatos):
            escolhido = topo.candidatos[topo.proximo_indice]
            topo.proximo_indice += 1

            caminho_atual.append(escolhido.candidato)
            visitadas.add(escolhido.candidato)
            metricas.registrar_estado()
            estados_nesta_busca += 1

            if not escolhido.completo_ainda_possivel:
                metricas.registrar_estado_sem_completo_possivel()

            if len(caminho_atual) > len(melhor_caminho):
                melhor_caminho = caminho_atual.copy()

            if len(caminho_atual) == total_casas:
                return melhor_caminho, "completo"

            if estados_nesta_busca >= max_estados:
                return melhor_caminho, "limite_estados"

            proximos_candidatos = _obter_candidatos(
                atual=escolhido.candidato,
                visitadas=visitadas,
                adjacencias=adjacencias,
                variante=variante,
                rng=rng,
                metricas=metricas,
                podar_inviaveis=podar_inviaveis,
            )
            pilha.append(_QuadroBusca(candidatos=proximos_candidatos))
        else:
            pilha.pop()
            if len(caminho_atual) > 1:
                removida = caminho_atual.pop()
                visitadas.remove(removida)
                metricas.registrar_recuo()

    return melhor_caminho, "busca_esgotada"
