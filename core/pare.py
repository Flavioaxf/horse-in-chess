from __future__ import annotations

from collections import deque
import random

from core.metrics import RegistradorMetricas
from core.tipos import (
    Adjacencias,
    AvaliacaoCandidato,
    MotivoParada,
    Posicao,
    VARIANTES_VALIDAS,
    VariantePARE,
)


def _validar_variante(variante: VariantePARE) -> None:
    if variante not in VARIANTES_VALIDAS:
        raise ValueError(
            f"Variante PARE inválida: {variante!r}. "
            f"Valores aceitos: {sorted(VARIANTES_VALIDAS)}."
        )


def chave_ordenacao(
    avaliacao: AvaliacaoCandidato,
    variante: VariantePARE,
) -> tuple[int, int, int, int]:
    """Retorna a chave lexicográfica minimizada pela variante configurada.

    Não usa pesos arbitrários; compara estritamente na ordem ``(F, I, P, ±A)``:
    - ``"restritiva"``: ``(F, I, P, +A)`` (prefere menos saídas imediatas).
    - ``"expansiva"``: ``(F, I, P, -A)`` (prefere mais saídas imediatas).

    Args:
        avaliacao: Indicadores estruturais ``(F, I, P, A)`` do candidato.
        variante: Variante da estratégia PARE (``"restritiva"`` ou ``"expansiva"``).

    Returns:
        Tupla de 4 inteiros usada como chave de ordenação crescente.

    Raises:
        ValueError: Se ``variante`` não for ``"restritiva"`` nem ``"expansiva"``.
    """
    _validar_variante(variante)
    termo_acessibilidade = (
        avaliacao.acessibilidade
        if variante == "restritiva"
        else -avaliacao.acessibilidade
    )
    return (
        avaliacao.fragmentacao,
        avaliacao.isolamento,
        avaliacao.pressao,
        termo_acessibilidade,
    )


def avaliar_candidato(
    candidato: Posicao,
    visitadas: set[Posicao],
    adjacencias: Adjacencias,
    metricas: RegistradorMetricas,
) -> AvaliacaoCandidato:
    """Simula a entrada em ``candidato`` e calcula ``(F, I, P, A)`` no grafo residual ``G_v``.

    O grafo residual ``G_v`` é induzido por ``{v} ∪ U``, onde ``v = candidato`` e
    ``U`` é o conjunto das casas não visitadas após entrar em ``v`` (``v ∉ U``).
    Os indicadores são obtidos em uma única passagem BFS sobre ``G_v``:
    - ``F`` (fragmentação): número de componentes conexas de ``G_v``.
    - ``I`` (isolamento): vértices de ``U`` (excluindo ``v``) com grau residual 0.
    - ``P`` (pressão): vértices de ``U`` (excluindo ``v``) com grau residual 1.
    - ``A`` (acessibilidade): grau de ``v`` em ``G_v`` (vizinhos de ``v`` em ``U``).
    - ``completo_ainda_possivel``: sinalizador da Proposição 5.3
      (``F == 1 and I == 0 and P <= 1``).

    O conjunto ``visitadas`` recebido não é modificado.

    Args:
        candidato: Casa candidata ``v = (linha, coluna)`` em índices 0-based.
        visitadas: Conjunto de casas já visitadas antes de entrar em ``candidato``.
        adjacencias: Mapa pré-calculado de listas de adjacência do grafo.
        metricas: Registrador centralizado de métricas da execução.

    Returns:
        ``AvaliacaoCandidato`` com os indicadores reais calculados sobre ``G_v``.

    Raises:
        ValueError: Se ``candidato`` não pertencer a ``adjacencias`` ou já estiver
            em ``visitadas``.
    """
    if candidato not in adjacencias:
        raise ValueError(
            f"Candidato inválido: {candidato!r} não pertence ao grafo de adjacências."
        )
    if candidato in visitadas:
        raise ValueError(
            f"Candidato inválido: {candidato!r} já consta no conjunto de casas visitadas."
        )

    metricas.registrar_avaliacao_candidato()

    vertices_residuais: set[Posicao] = {
        casa for casa in adjacencias if casa not in visitadas
    }
    explorados: set[Posicao] = set()
    fila: deque[Posicao] = deque()

    fragmentacao = 0
    isolamento = 0
    pressao = 0
    acessibilidade = 0

    for origem in vertices_residuais:
        if origem in explorados:
            continue

        fragmentacao += 1
        explorados.add(origem)
        fila.append(origem)

        while fila:
            vertice = fila.popleft()
            vizinhos = adjacencias[vertice]
            metricas.registrar_verificacao_movimento(len(vizinhos))

            grau_residual = 0
            for vizinho in vizinhos:
                if vizinho in vertices_residuais and vizinho != vertice:
                    grau_residual += 1
                    if vizinho not in explorados:
                        explorados.add(vizinho)
                        fila.append(vizinho)

            if vertice == candidato:
                acessibilidade = grau_residual
            elif grau_residual == 0:
                isolamento += 1
            elif grau_residual == 1:
                pressao += 1

    completo_ainda_possivel = (
        fragmentacao == 1 and isolamento == 0 and pressao <= 1
    )
    return AvaliacaoCandidato(
        candidato=candidato,
        fragmentacao=fragmentacao,
        isolamento=isolamento,
        pressao=pressao,
        acessibilidade=acessibilidade,
        completo_ainda_possivel=completo_ainda_possivel,
    )


def ordenar_candidatos(
    atual: Posicao,
    visitadas: set[Posicao],
    adjacencias: Adjacencias,
    variante: VariantePARE,
    rng: random.Random,
    metricas: RegistradorMetricas,
) -> list[AvaliacaoCandidato]:
    """Enumera, avalia e ordena todos os movimentos válidos a partir de ``atual``.

    A ordenação define apenas prioridade — nenhum candidato válido é descartado
    por pontuação ou pelo sinalizador ``completo_ainda_possivel``. Empates exatos
    na chave lexicográfica são quebrados de forma determinística pelo gerador
    local ``rng``.

    Args:
        atual: Posição corrente do cavalo (já pertencente a ``visitadas``).
        visitadas: Conjunto de casas já visitadas no percurso atual.
        adjacencias: Mapa pré-calculado de listas de adjacência do grafo.
        variante: Variante PARE (``"restritiva"`` ou ``"expansiva"``).
        rng: Gerador pseudoaleatório local (``random.Random(seed)``).
        metricas: Registrador centralizado de métricas da execução.

    Returns:
        Lista com todas as avaliações de candidatos válidos ordenadas por prioridade.

    Raises:
        ValueError: Se ``variante`` for inválida, se ``atual`` não pertencer a
            ``adjacencias`` ou se ``atual`` não estiver em ``visitadas``.
    """
    _validar_variante(variante)
    if atual not in adjacencias:
        raise ValueError(
            f"Posição atual inválida: {atual!r} não pertence ao grafo de adjacências."
        )
    if atual not in visitadas:
        raise ValueError(
            f"Posição atual inválida: {atual!r} deve estar presente em visitadas."
        )

    vizinhos_atual = adjacencias[atual]
    metricas.registrar_verificacao_movimento(len(vizinhos_atual))
    candidatos = [vizinho for vizinho in vizinhos_atual if vizinho not in visitadas]

    avaliacoes = [
        avaliar_candidato(candidato, visitadas, adjacencias, metricas)
        for candidato in candidatos
    ]

    if len(avaliacoes) > 1:
        rng.shuffle(avaliacoes)
        avaliacoes.sort(key=lambda avaliacao: chave_ordenacao(avaliacao, variante))

    return avaliacoes


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def executar_guloso(
    n: int,
    inicio: Posicao,
    variante: VariantePARE,
    adjacencias: Adjacencias,
    rng: random.Random,
    metricas: RegistradorMetricas,
) -> tuple[list[Posicao], MotivoParada]:
    """Executa a estratégia PARE no modo guloso (sem recuo; ``recuos == 0``).

    A partir de ``inicio``, avança iterativamente para o candidato de maior
    prioridade segundo ``ordenar_candidatos`` até visitar todas as ``n * n``
    casas ou não haver mais movimentos válidos. Nunca desfaz escolhas nem
    descarta candidatos pelo sinalizador da Proposição 5.3.

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

    Raises:
        ValueError: Se ``n`` não for inteiro positivo, se ``variante`` for
            inválida, se ``adjacencias`` não corresponder a um tabuleiro ``n × n``
            ou se ``inicio`` não pertencer a ``adjacencias``.
    """
    if not _eh_inteiro_estrito(n) or n <= 0:
        raise ValueError(
            f"Dimensão inválida no modo guloso: esperado inteiro positivo, recebido {n!r}."
        )
    _validar_variante(variante)

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

    caminho: list[Posicao] = [inicio]
    visitadas: set[Posicao] = {inicio}
    metricas.registrar_estado()

    while len(caminho) < total_casas:
        atual = caminho[-1]
        candidatos_ordenados = ordenar_candidatos(
            atual=atual,
            visitadas=visitadas,
            adjacencias=adjacencias,
            variante=variante,
            rng=rng,
            metricas=metricas,
        )
        if not candidatos_ordenados:
            return caminho, "sem_movimentos"

        escolhido = candidatos_ordenados[0]
        caminho.append(escolhido.candidato)
        visitadas.add(escolhido.candidato)
        metricas.registrar_estado()
        if not escolhido.completo_ainda_possivel:
            metricas.registrar_estado_sem_completo_possivel()

    return caminho, "completo"
