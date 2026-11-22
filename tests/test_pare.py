from __future__ import annotations

import random
import subprocess

import pytest

import cli
import core.api as api_module
from core.api import obter_versao_codigo, resolver
from core.board import KNIGHT_MOVES, gerar_adjacencias
from core.metrics import RegistradorMetricas
from core.pare import (
    avaliar_candidato,
    chave_ordenacao,
    executar_guloso,
    ordenar_candidatos,
)
from core.tipos import (
    Adjacencias,
    AvaliacaoCandidato,
    ConfiguracaoExecucao,
    Posicao,
    ResultadoExecucao,
)
from core.validator import validar_percurso


def _criar_grafo(arestas: list[tuple[Posicao, Posicao]], vertices: list[Posicao]) -> Adjacencias:
    vizinhos_por_vertice: dict[Posicao, list[Posicao]] = {v: [] for v in vertices}
    for u, v in arestas:
        if v not in vizinhos_por_vertice[u]:
            vizinhos_por_vertice[u].append(v)
        if u not in vizinhos_por_vertice[v]:
            vizinhos_por_vertice[v].append(u)
    return {v: tuple(vizinhos) for v, vizinhos in vizinhos_por_vertice.items()}


def _gerar_adjacencias_retangular(linhas: int, colunas: int) -> Adjacencias:
    adjacencias: Adjacencias = {}
    for linha in range(linhas):
        for coluna in range(colunas):
            vizinhos: list[Posicao] = []
            for dl, dc in KNIGHT_MOVES:
                nl, nc = linha + dl, coluna + dc
                if 0 <= nl < linhas and 0 <= nc < colunas:
                    vizinhos.append((nl, nc))
            adjacencias[(linha, coluna)] = tuple(vizinhos)
    return adjacencias


def _existe_caminho_hamiltoniano(
    inicio: Posicao,
    vertices_alvo: set[Posicao],
    adjacencias: Adjacencias,
) -> bool:
    total = len(vertices_alvo)
    if inicio not in vertices_alvo:
        return False
    if total == 1:
        return True

    visitados: set[Posicao] = {inicio}

    def dfs(atual: Posicao) -> bool:
        if len(visitados) == total:
            return True
        for vizinho in adjacencias[atual]:
            if vizinho in vertices_alvo and vizinho not in visitados:
                visitados.add(vizinho)
                if dfs(vizinho):
                    return True
                visitados.remove(vizinho)
        return False

    return dfs(inicio)

def test_avaliar_candidato_ultima_casa_restante_u_vazio() -> None:
    u, v = (0, 0), (1, 2)
    adjacencias = _criar_grafo([(u, v)], [u, v])
    visitadas = {u}
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, visitadas, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=1,
        isolamento=0,
        pressao=0,
        acessibilidade=0,
        completo_ainda_possivel=True,
    )
    assert visitadas == {u}
    assert metricas.avaliacoes_candidatos == 1
    assert metricas.verificacoes_movimentos == len(adjacencias[v])


def test_avaliar_candidato_caminho_dois_vertices_no_residual() -> None:
    u, v, c = (0, 0), (1, 2), (2, 0)
    adjacencias = _criar_grafo([(u, v), (v, c)], [u, v, c])
    visitadas = {u}
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, visitadas, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=1,
        isolamento=0,
        pressao=1,
        acessibilidade=1,
        completo_ainda_possivel=True,
    )
    assert metricas.avaliacoes_candidatos == 1
    assert metricas.verificacoes_movimentos == len(adjacencias[v]) + len(adjacencias[c])


def test_avaliar_candidato_estrela_gera_pressao_dois() -> None:
    u, v, x, y = (0, 0), (1, 2), (0, 4), (3, 1)
    adjacencias = _criar_grafo([(u, v), (v, x), (v, y)], [u, v, x, y])
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, {u}, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=1,
        isolamento=0,
        pressao=2,
        acessibilidade=2,
        completo_ainda_possivel=False,
    )


def test_avaliar_candidato_exclui_v_de_isolamento_i() -> None:
    u, v, x, y, z = (0, 0), (1, 2), (3, 3), (4, 0), (2, 1)
    adjacencias = _criar_grafo([(u, v), (y, z)], [u, v, x, y, z])
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, {u}, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=3,
        isolamento=1,
        pressao=2,
        acessibilidade=0,
        completo_ainda_possivel=False,
    )


def test_avaliar_candidato_exclui_v_de_pressao_p() -> None:
    u, v, x, y, z = (0, 0), (0, 1), (0, 2), (0, 3), (0, 4)
    adjacencias = _criar_grafo(
        [(u, v), (v, x), (x, y), (y, z), (z, x)],
        [u, v, x, y, z],
    )
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, {u}, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=1,
        isolamento=0,
        pressao=0,
        acessibilidade=1,
        completo_ainda_possivel=True,
    )


def test_avaliar_candidato_grafo_desconexo_com_dois_triangulos() -> None:
    u = (0, 0)
    v, a, b = (1, 0), (1, 1), (1, 2)
    c, d, e = (2, 0), (2, 1), (2, 2)
    adjacencias = _criar_grafo(
        [(u, v), (v, a), (a, b), (b, v), (c, d), (d, e), (e, c)],
        [u, v, a, b, c, d, e],
    )
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, {u}, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=v,
        fragmentacao=2,
        isolamento=0,
        pressao=0,
        acessibilidade=2,
        completo_ainda_possivel=False,
    )


def test_avaliar_candidato_tabuleiro_3x3_real_conferido_a_mao() -> None:
    adjacencias = gerar_adjacencias(3)
    visitadas = {(0, 0)}
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato((1, 2), visitadas, adjacencias, metricas)

    assert avaliacao == AvaliacaoCandidato(
        candidato=(1, 2),
        fragmentacao=2,
        isolamento=1,
        pressao=1,
        acessibilidade=1,
        completo_ainda_possivel=False,
    )
    assert metricas.avaliacoes_candidatos == 1
    assert metricas.verificacoes_movimentos == 14


def test_avaliar_candidato_rejeita_entradas_invalidas_sem_poluir_metricas() -> None:
    adjacencias = gerar_adjacencias(5)
    metricas = RegistradorMetricas()

    with pytest.raises(ValueError):
        avaliar_candidato((9, 9), {(0, 0)}, adjacencias, metricas)

    with pytest.raises(ValueError):
        avaliar_candidato((0, 0), {(0, 0)}, adjacencias, metricas)

    assert metricas.avaliacoes_candidatos == 0
    assert metricas.verificacoes_movimentos == 0

def test_proposicao_5_3_forca_bruta_em_tabuleiro_retangular_3x4() -> None:
    adjacencias = _gerar_adjacencias_retangular(3, 4)
    metricas = RegistradorMetricas()

    casos_com_passeio = 0
    casos_sem_passeio = 0

    for inicio in adjacencias:
        visitadas = {inicio}
        vertices_residuais = set(adjacencias) - visitadas
        for candidato in adjacencias[inicio]:
            avaliacao = avaliar_candidato(candidato, visitadas, adjacencias, metricas)
            existe_passeio = _existe_caminho_hamiltoniano(
                candidato, vertices_residuais, adjacencias
            )

            if existe_passeio:
                casos_com_passeio += 1
                assert avaliacao.fragmentacao == 1
                assert avaliacao.isolamento == 0
                assert avaliacao.pressao <= 1
                assert avaliacao.completo_ainda_possivel is True
            else:
                casos_sem_passeio += 1

    assert casos_com_passeio > 0
    assert casos_sem_passeio > 0


def test_proposicao_5_3_forca_bruta_em_subestados_reais_do_5x5() -> None:
    adjacencias = gerar_adjacencias(5)
    metricas = RegistradorMetricas()

    caminho_parcial_valido: list[Posicao] = [
        (0, 0), (1, 2), (0, 4), (2, 3), (4, 4), (3, 2), (4, 0), (2, 1),
        (0, 2), (1, 4), (3, 3), (4, 1), (2, 0), (0, 1), (1, 3), (3, 4), (4, 2),
    ]

    casos_com_passeio = 0
    casos_sem_passeio = 0

    for tamanho in (15, 16, 17):
        prefixo = caminho_parcial_valido[:tamanho]
        atual = prefixo[-1]
        visitadas = set(prefixo)
        vertices_residuais = set(adjacencias) - visitadas

        for candidato in adjacencias[atual]:
            if candidato in visitadas:
                continue
            avaliacao = avaliar_candidato(candidato, visitadas, adjacencias, metricas)
            existe_passeio = _existe_caminho_hamiltoniano(
                candidato, vertices_residuais, adjacencias
            )
            if existe_passeio:
                casos_com_passeio += 1
                assert avaliacao.fragmentacao == 1
                assert avaliacao.isolamento == 0
                assert avaliacao.pressao <= 1
                assert avaliacao.completo_ainda_possivel is True
            else:
                casos_sem_passeio += 1

    assert casos_com_passeio > 0
    assert casos_sem_passeio >= 0


def test_proposicao_5_3_eh_necessaria_mas_nao_suficiente() -> None:
    u = (9, 9)
    esquerda = [(0, 0), (0, 1)]
    direita = [(1, 0), (1, 1), (1, 2), (1, 3)]
    v = direita[0]

    arestas: list[tuple[Posicao, Posicao]] = [(u, v)]
    for e in esquerda:
        for d in direita:
            arestas.append((e, d))

    adjacencias = _criar_grafo(arestas, [u, *esquerda, *direita])
    visitadas = {u}
    vertices_residuais = set(adjacencias) - visitadas
    metricas = RegistradorMetricas()

    avaliacao = avaliar_candidato(v, visitadas, adjacencias, metricas)

    assert avaliacao.fragmentacao == 1
    assert avaliacao.isolamento == 0
    assert avaliacao.pressao == 0
    assert avaliacao.acessibilidade == 2
    assert avaliacao.completo_ainda_possivel is True
    assert _existe_caminho_hamiltoniano(v, vertices_residuais, adjacencias) is False

def test_chave_ordenacao_restritiva_e_expansiva() -> None:
    avaliacao = AvaliacaoCandidato(
        candidato=(2, 1),
        fragmentacao=1,
        isolamento=2,
        pressao=3,
        acessibilidade=5,
        completo_ainda_possivel=False,
    )

    assert chave_ordenacao(avaliacao, "restritiva") == (1, 2, 3, 5)
    assert chave_ordenacao(avaliacao, "expansiva") == (1, 2, 3, -5)

    with pytest.raises(ValueError):
        chave_ordenacao(avaliacao, "invalida")  # type: ignore[arg-type]


@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_chave_ordenacao_prioridade_lexicografica_estrita_sem_pesos(
    variante: str,
) -> None:
    menor_f = AvaliacaoCandidato((0, 0), 1, 99, 99, 8, False)
    maior_f = AvaliacaoCandidato((0, 1), 2, 0, 0, 0, False)
    assert chave_ordenacao(menor_f, variante) < chave_ordenacao(maior_f, variante)  # type: ignore[arg-type]

    menor_i = AvaliacaoCandidato((0, 0), 1, 0, 99, 8, False)
    maior_i = AvaliacaoCandidato((0, 1), 1, 1, 0, 0, False)
    assert chave_ordenacao(menor_i, variante) < chave_ordenacao(maior_i, variante)  # type: ignore[arg-type]

    menor_p = AvaliacaoCandidato((0, 0), 1, 0, 0, 8, True)
    maior_p = AvaliacaoCandidato((0, 1), 1, 0, 1, 0, True)
    assert chave_ordenacao(menor_p, variante) < chave_ordenacao(maior_p, variante)  # type: ignore[arg-type]


def test_variantes_escolhem_menor_ou_maior_acessibilidade_com_mesmos_fip() -> None:
    atual = (0, 0)
    v1 = (1, 2)
    v2 = (2, 1)
    x, y, z = (3, 0), (3, 1), (3, 2)

    adjacencias = _criar_grafo(
        [
            (atual, v1),
            (atual, v2),
            (v1, x),
            (v1, y),
            (v2, x),
            (v2, y),
            (v2, z),
            (x, y),
            (y, z),
            (z, x),
        ],
        [atual, v1, v2, x, y, z],
    )
    visitadas = {atual}

    metricas_r = RegistradorMetricas()
    ord_r = ordenar_candidatos(
        atual, visitadas, adjacencias, "restritiva", random.Random(2026), metricas_r
    )

    metricas_e = RegistradorMetricas()
    ord_e = ordenar_candidatos(
        atual, visitadas, adjacencias, "expansiva", random.Random(2026), metricas_e
    )

    assert [a.candidato for a in ord_r] == [v1, v2]
    assert [a.candidato for a in ord_e] == [v2, v1]

    assert (ord_r[0].fragmentacao, ord_r[0].isolamento, ord_r[0].pressao) == (1, 0, 0)
    assert (ord_r[1].fragmentacao, ord_r[1].isolamento, ord_r[1].pressao) == (1, 0, 0)
    assert ord_r[0].acessibilidade == 2
    assert ord_r[1].acessibilidade == 3


def test_variantes_em_tabuleiro_8x8_real_divergem_em_acessibilidade() -> None:
    adjacencias = gerar_adjacencias(8)
    atual = (2, 2)
    visitadas = {(2, 2)}

    ord_r = ordenar_candidatos(
        atual,
        visitadas,
        adjacencias,
        "restritiva",
        random.Random(2026),
        RegistradorMetricas(),
    )
    ord_e = ordenar_candidatos(
        atual,
        visitadas,
        adjacencias,
        "expansiva",
        random.Random(2026),
        RegistradorMetricas(),
    )

    assert len(ord_r) == len(ord_e) == 8
    assert all((a.fragmentacao, a.isolamento, a.pressao) == (1, 0, 0) for a in ord_r)
    assert all((a.fragmentacao, a.isolamento, a.pressao) == (1, 0, 0) for a in ord_e)
    assert ord_r[0].acessibilidade == 2
    assert ord_r[0].candidato in {(0, 1), (1, 0)}
    assert ord_e[0].acessibilidade == 7
    assert ord_e[0].candidato in {(3, 4), (4, 3)}
    assert [a.acessibilidade for a in ord_r] == [2, 2, 3, 3, 5, 5, 7, 7]
    assert [a.acessibilidade for a in ord_e] == [7, 7, 5, 5, 3, 3, 2, 2]


def test_ordenar_candidatos_define_prioridade_sem_excluir_inviaveis() -> None:
    atual = (0, 0)
    v_bom = (1, 0)
    v_ruim = (1, 1)
    ponta = (2, 1)
    meio = (2, 0)

    adjacencias = _criar_grafo(
        [
            (atual, v_bom),
            (atual, v_ruim),
            (v_bom, meio),
            (meio, v_ruim),
            (v_ruim, ponta),
        ],
        [atual, v_bom, v_ruim, meio, ponta],
    )
    visitadas = {atual}
    metricas = RegistradorMetricas()

    ordenados = ordenar_candidatos(
        atual, visitadas, adjacencias, "restritiva", random.Random(2026), metricas
    )

    assert len(ordenados) == 2
    assert ordenados[0].candidato == v_bom
    assert ordenados[0].completo_ainda_possivel is True
    assert ordenados[1].candidato == v_ruim
    assert ordenados[1].completo_ainda_possivel is False
    assert metricas.avaliacoes_candidatos == 2
    assert visitadas == {atual}


def test_ordenar_candidatos_sem_movimentos_retorna_vazio_e_contabiliza_leitura() -> None:
    adjacencias = gerar_adjacencias(5)
    atual = (0, 0)
    visitadas = {(0, 0), (1, 2), (2, 1)}
    metricas = RegistradorMetricas()

    ordenados = ordenar_candidatos(
        atual, visitadas, adjacencias, "restritiva", random.Random(2026), metricas
    )

    assert ordenados == []
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.verificacoes_movimentos == len(adjacencias[atual])


def test_ordenar_candidatos_rejeita_entradas_invalidas() -> None:
    adjacencias = gerar_adjacencias(5)
    metricas = RegistradorMetricas()

    with pytest.raises(ValueError):
        ordenar_candidatos(
            (0, 0), {(0, 0)}, adjacencias, "desconhecida", random.Random(1), metricas  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError):
        ordenar_candidatos(
            (9, 9), {(9, 9)}, adjacencias, "restritiva", random.Random(1), metricas
        )

    with pytest.raises(ValueError):
        ordenar_candidatos(
            (0, 0), set(), adjacencias, "restritiva", random.Random(1), metricas
        )

    assert metricas.avaliacoes_candidatos == 0
    assert metricas.verificacoes_movimentos == 0

@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_ordenar_candidatos_determinismo_com_mesma_semente(variante: str) -> None:
    adjacencias = gerar_adjacencias(5)
    atual = (2, 2)
    visitadas = {(2, 2)}

    metricas_1 = RegistradorMetricas()
    metricas_2 = RegistradorMetricas()

    res_1 = ordenar_candidatos(
        atual, visitadas, adjacencias, variante, random.Random(2026), metricas_1  # type: ignore[arg-type]
    )
    res_2 = ordenar_candidatos(
        atual, visitadas, adjacencias, variante, random.Random(2026), metricas_2  # type: ignore[arg-type]
    )

    assert res_1 == res_2
    assert metricas_1.avaliacoes_candidatos == metricas_2.avaliacoes_candidatos == 8
    assert metricas_1.verificacoes_movimentos == metricas_2.verificacoes_movimentos


def test_ordenar_candidatos_desempata_com_rng_local_sem_alterar_random_global() -> None:
    adjacencias = gerar_adjacencias(5)
    atual = (0, 0)
    visitadas = {(0, 0)}

    estado_global_antes = random.getstate()
    ordens_observadas: set[tuple[Posicao, Posicao]] = set()

    for seed in range(25):
        ordenados = ordenar_candidatos(
            atual,
            visitadas,
            adjacencias,
            "restritiva",
            random.Random(seed),
            RegistradorMetricas(),
        )
        assert ordenados[0].fragmentacao == ordenados[1].fragmentacao
        assert ordenados[0].isolamento == ordenados[1].isolamento
        assert ordenados[0].pressao == ordenados[1].pressao
        assert ordenados[0].acessibilidade == ordenados[1].acessibilidade
        ordens_observadas.add((ordenados[0].candidato, ordenados[1].candidato))

    estado_global_depois = random.getstate()
    assert estado_global_antes == estado_global_depois
    assert ordens_observadas == {((1, 2), (2, 1)), ((2, 1), (1, 2))}

def test_executar_guloso_1x1_completo_imediato() -> None:
    adjacencias = gerar_adjacencias(1)
    metricas = RegistradorMetricas()

    caminho, motivo = executar_guloso(
        n=1,
        inicio=(0, 0),
        variante="restritiva",
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas,
    )

    assert caminho == [(0, 0)]
    assert motivo == "completo"
    assert metricas.estados_explorados == 1
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.verificacoes_movimentos == 0
    assert metricas.recuos == 0
    assert metricas.estados_sem_completo_possivel == 0


def test_executar_guloso_3x3_percorre_borda_sem_podar_e_para_sem_movimentos() -> None:
    adjacencias = gerar_adjacencias(3)
    metricas = RegistradorMetricas()

    caminho, motivo = executar_guloso(
        n=3,
        inicio=(0, 0),
        variante="restritiva",
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas,
    )

    validacao = validar_percurso(3, (0, 0), caminho)
    assert validacao.valido is True
    assert validacao.passeio_completo is False
    assert len(caminho) == 8
    assert (1, 1) not in caminho
    assert motivo == "sem_movimentos"
    assert metricas.estados_explorados == 8
    assert metricas.recuos == 0
    assert metricas.estados_sem_completo_possivel == 7


@pytest.mark.parametrize(
    ("n", "inicio", "variante"),
    [
        (5, (0, 0), "restritiva"),
        (5, (0, 0), "expansiva"),
        (5, (0, 1), "restritiva"),
        (8, (0, 0), "restritiva"),
        (8, (3, 3), "expansiva"),
    ],
)
def test_executar_guloso_gera_percurso_valido_sem_recuos(
    n: int,
    inicio: Posicao,
    variante: str,
) -> None:
    adjacencias = gerar_adjacencias(n)
    metricas = RegistradorMetricas()

    caminho, motivo = executar_guloso(
        n=n,
        inicio=inicio,
        variante=variante,  # type: ignore[arg-type]
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas,
    )

    validacao = validar_percurso(n, inicio, caminho)
    assert validacao.valido is True
    assert caminho[0] == inicio
    assert metricas.recuos == 0
    assert metricas.estados_explorados == len(caminho)
    assert 1 <= len(caminho) <= n * n
    if len(caminho) == n * n:
        assert motivo == "completo"
        assert validacao.passeio_completo is True
    else:
        assert motivo == "sem_movimentos"
        assert validacao.passeio_completo is False


def test_executar_guloso_rejeita_entradas_invalidas() -> None:
    adjacencias_5 = gerar_adjacencias(5)
    metricas = RegistradorMetricas()

    with pytest.raises(ValueError):
        executar_guloso(0, (0, 0), "restritiva", adjacencias_5, random.Random(1), metricas)

    with pytest.raises(ValueError):
        executar_guloso(True, (0, 0), "restritiva", adjacencias_5, random.Random(1), metricas)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        executar_guloso(5, (0, 0), "invalida", adjacencias_5, random.Random(1), metricas)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        executar_guloso(8, (0, 0), "restritiva", adjacencias_5, random.Random(1), metricas)

    with pytest.raises(ValueError):
        executar_guloso(5, (9, 9), "restritiva", adjacencias_5, random.Random(1), metricas)

    assert metricas.estados_explorados == 0


def test_obter_versao_codigo_retorna_string_e_trata_falha_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versao_real = obter_versao_codigo()
    assert isinstance(versao_real, str)
    assert len(versao_real) > 0

    def falha_os(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("git indisponível")

    monkeypatch.setattr(api_module.subprocess, "run", falha_os)
    assert obter_versao_codigo() == "desconhecida"

    def retorno_erro(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=128, stdout="", stderr="err")

    monkeypatch.setattr(api_module.subprocess, "run", retorno_erro)
    assert obter_versao_codigo() == "desconhecida"


@pytest.mark.parametrize(
    ("n", "inicio", "paridade_esperada"),
    [
        (5, (0, 0), False),
        (5, (0, 1), True),
        (8, (0, 0), False),
        (8, (3, 3), False),
    ],
)
@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_resolver_guloso_cenarios_obrigatorios_e_invariantes(
    n: int,
    inicio: Posicao,
    paridade_esperada: bool,
    variante: str,
) -> None:
    config = ConfiguracaoExecucao(
        n=n,
        inicio=inicio,
        modo="guloso",
        variante=variante,  # type: ignore[arg-type]
        seed=2026,
    )

    resultado = resolver(config)

    assert isinstance(resultado, ResultadoExecucao)
    assert resultado.config == config
    assert resultado.seed_utilizada == 2026
    assert resultado.total_casas == n * n
    assert resultado.casas_visitadas == len(resultado.melhor_percurso)
    assert resultado.cobertura_percentual == pytest.approx(
        100.0 * resultado.casas_visitadas / resultado.total_casas
    )
    assert resultado.impossibilidade_paridade is paridade_esperada
    assert resultado.recuos == 0
    assert resultado.estados_explorados == resultado.casas_visitadas
    assert resultado.verificacoes_preparo == 8 * n * n
    assert resultado.verificacoes_movimentos > 0
    assert resultado.avaliacoes_candidatos > 0
    assert resultado.tempo_segundos >= 0.0
    assert isinstance(resultado.versao_codigo, str) and len(resultado.versao_codigo) > 0

    validacao = validar_percurso(n, inicio, resultado.melhor_percurso)
    assert validacao.valido is True
    assert resultado.melhor_percurso[0] == inicio
    assert resultado.passeio_completo is validacao.passeio_completo
    assert resultado.motivo_parada == (
        "completo" if resultado.passeio_completo else "sem_movimentos"
    )

    if paridade_esperada:
        assert resultado.passeio_completo is False
        assert resultado.casas_visitadas <= 24
        assert resultado.casas_visitadas > 1


@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_resolver_guloso_determinismo_com_mesma_semente(variante: str) -> None:
    config = ConfiguracaoExecucao(
        n=8,
        inicio=(3, 3),
        modo="guloso",
        variante=variante,  # type: ignore[arg-type]
        seed=2026,
    )

    r1 = resolver(config)
    r2 = resolver(config)

    assert r1.seed_utilizada == r2.seed_utilizada == 2026
    assert r1.melhor_percurso == r2.melhor_percurso
    assert r1.casas_visitadas == r2.casas_visitadas
    assert r1.cobertura_percentual == r2.cobertura_percentual
    assert r1.passeio_completo == r2.passeio_completo
    assert r1.motivo_parada == r2.motivo_parada
    assert r1.estados_explorados == r2.estados_explorados
    assert r1.verificacoes_movimentos == r2.verificacoes_movimentos
    assert r1.verificacoes_preparo == r2.verificacoes_preparo
    assert r1.avaliacoes_candidatos == r2.avaliacoes_candidatos
    assert r1.recuos == r2.recuos == 0
    assert r1.estados_sem_completo_possivel == r2.estados_sem_completo_possivel


def test_resolver_gera_e_registra_seed_quando_none_sem_afetar_random_global() -> None:
    estado_global_antes = random.getstate()
    cfg_sem_seed = ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", seed=None)

    res_auto = resolver(cfg_sem_seed)

    assert random.getstate() == estado_global_antes
    assert isinstance(res_auto.seed_utilizada, int)
    assert not isinstance(res_auto.seed_utilizada, bool)

    cfg_reproduzida = ConfiguracaoExecucao(
        n=5, inicio=(0, 0), modo="guloso", seed=res_auto.seed_utilizada
    )
    res_reproduzido = resolver(cfg_reproduzida)
    assert res_reproduzido.melhor_percurso == res_auto.melhor_percurso
    assert res_reproduzido.estados_explorados == res_auto.estados_explorados
    assert res_reproduzido.verificacoes_movimentos == res_auto.verificacoes_movimentos


@pytest.mark.parametrize(
    "config_invalida",
    [
        ConfiguracaoExecucao(n=6, inicio=(0, 0), modo="guloso"),
        ConfiguracaoExecucao(n=5, inicio=(5, 0), modo="guloso"),
        ConfiguracaoExecucao(n=5, inicio=(-1, 0), modo="guloso"),
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="invalido"),  # type: ignore[arg-type]
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", variante="outra"),  # type: ignore[arg-type]
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", seed=True),  # type: ignore[arg-type]
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", seed="2026"),  # type: ignore[arg-type]
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", max_estados=0),
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", max_estados=-5),
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", podar_inviaveis=1),  # type: ignore[arg-type]
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="recuo", max_estados=None),
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="recuo", max_estados=0),
        ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="recuo", max_estados=True),  # type: ignore[arg-type]
    ],
)
def test_resolver_rejeita_configuracoes_invalidas(
    config_invalida: ConfiguracaoExecucao,
) -> None:
    with pytest.raises(ValueError):
        resolver(config_invalida)


def test_resolver_rejeita_objeto_que_nao_e_configuracao() -> None:
    with pytest.raises(ValueError):
        resolver({"n": 5, "inicio": (0, 0), "modo": "guloso"})  # type: ignore[arg-type]


def test_resolver_despacha_modo_recuo_com_todos_os_parametros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamada: dict[str, object] = {}

    def recuo_duble(
        n: int,
        inicio: Posicao,
        variante: str,
        max_estados: int,
        adjacencias: Adjacencias,
        rng: random.Random,
        metricas: RegistradorMetricas,
        podar_inviaveis: bool = False,
    ) -> tuple[list[Posicao], str]:
        chamada["n"] = n
        chamada["inicio"] = inicio
        chamada["variante"] = variante
        chamada["max_estados"] = max_estados
        chamada["total_adj"] = len(adjacencias)
        chamada["podar_inviaveis"] = podar_inviaveis
        metricas.registrar_estado()
        metricas.registrar_estado()
        metricas.registrar_recuo()
        return [inicio, (1, 2)], "limite_estados"

    monkeypatch.setattr(api_module, "executar_recuo", recuo_duble)

    config = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 0),
        modo="recuo",
        variante="expansiva",
        seed=42,
        max_estados=250,
        podar_inviaveis=True,
    )
    resultado = resolver(config)

    assert chamada == {
        "n": 5,
        "inicio": (0, 0),
        "variante": "expansiva",
        "max_estados": 250,
        "total_adj": 25,
        "podar_inviaveis": True,
    }
    assert resultado.melhor_percurso == [(0, 0), (1, 2)]
    assert resultado.casas_visitadas == 2
    assert resultado.passeio_completo is False
    assert resultado.motivo_parada == "limite_estados"
    assert resultado.estados_explorados == 2
    assert resultado.recuos == 1


def test_resolver_recusa_percurso_invalido_ou_completo_inconsistente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def guloso_invalido(*args: object, **kwargs: object) -> tuple[list[Posicao], str]:
        # Casa repetida: deve ser rejeitada pelo validador independente.
        return [(0, 0), (1, 2), (0, 0)], "sem_movimentos"

    monkeypatch.setattr(api_module, "executar_guloso", guloso_invalido)
    with pytest.raises(RuntimeError, match="Percurso inválido"):
        resolver(ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", seed=1))

    def guloso_completo_falso(*args: object, **kwargs: object) -> tuple[list[Posicao], str]:
        # Percurso válido mas parcial alegando motivo_parada="completo".
        return [(0, 0), (1, 2)], "completo"

    monkeypatch.setattr(api_module, "executar_guloso", guloso_completo_falso)
    with pytest.raises(RuntimeError, match="Inconsistência interna"):
        resolver(ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="guloso", seed=1))


def test_integracao_cli_com_resolver_guloso_real(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = cli.main(
        [
            "--n",
            "5",
            "--linha",
            "1",
            "--coluna",
            "1",
            "--modo",
            "guloso",
            "--variante",
            "restritiva",
            "--seed",
            "2026",
        ]
    )
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "tabuleiro 5×5" in saida
    assert "início (linha 1, coluna 1)" in saida
    assert "semente utilizada ....... 2026" in saida
