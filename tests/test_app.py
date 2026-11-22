"""Testes da interface ``app.py`` (Dono: P3 — Flávio).

O ``resolver`` é substituído por um dublê que devolve um percurso **escrito à mão**
(definido em ``tests/test_render.py``), e o CSV de experimentos usado aqui é um
arquivo temporário com valores fictícios. Nada disso é usado pela interface real.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app
import core.api
import core.validator
from core.tipos import ConfiguracaoExecucao, ResultadoValidacao
from tests.test_render import PASSEIO_5X5_MANUAL, PERCURSO_PARCIAL_MANUAL, _resultado_manual

ARQUIVO_APP = str(Path(__file__).resolve().parent.parent / "app.py")


# --------------------------------------------------------------------------- formatação


def test_formatacao_brasileira() -> None:
    assert app.formatar_inteiro(10_000) == "10.000"
    assert app.formatar_decimal(1234.5) == "1.234,50"
    assert app.formatar_decimal(0.0012, 6) == "0,001200"
    assert app.formatar_casa((0, 4)) == "(1, 5)"


# --------------------------------------------------------------------------- configuração


def test_configuracao_converte_para_0_based() -> None:
    cfg = app.construir_configuracao(8, 4, 5, "recuo", "expansiva", 7, 500)
    assert cfg == ConfiguracaoExecucao(
        n=8, inicio=(3, 4), modo="recuo", variante="expansiva", seed=7, max_estados=500
    )


def test_configuracao_guloso_descarta_orcamento() -> None:
    cfg = app.construir_configuracao(5, 1, 1, "guloso", "restritiva", None, 500)
    assert cfg.max_estados is None and cfg.seed is None


@pytest.mark.parametrize(
    "args",
    [
        (6, 1, 1, "guloso", "restritiva", None, None),
        (5, 0, 1, "guloso", "restritiva", None, None),
        (5, 1, 6, "guloso", "restritiva", None, None),
        (5, 1, 1, "recuo", "restritiva", None, None),
        (5, 1, 1, "recuo", "restritiva", None, 0),
    ],
)
def test_configuracao_invalida_e_rejeitada(args) -> None:
    with pytest.raises(ValueError):
        app.construir_configuracao(*args)


# --------------------------------------------------------------------------- tabuleiro


def test_argumentos_do_tabuleiro_levam_exatamente_o_melhor_percurso() -> None:
    args = app.argumentos_tabuleiro("analise", 5, (0, 0), PERCURSO_PARCIAL_MANUAL,
                                    cor="preto", execucao=3)
    assert args["modo"] == "analise" and args["n"] == 5
    assert [tuple(p) for p in args["percurso"]] == PERCURSO_PARCIAL_MANUAL
    assert args["cor"] == "preto" and args["execucao"] == 3


def test_previa_nao_leva_percurso() -> None:
    args = app.argumentos_tabuleiro("previa", 8, (3, 3))
    assert args["percurso"] == [] and args["inicio"] == [3, 3] and args["cor"] == "azul"


@pytest.mark.parametrize(
    "modo, percurso, cor",
    [
        ("outro", PERCURSO_PARCIAL_MANUAL, "azul"),
        ("analise", PERCURSO_PARCIAL_MANUAL, "verde"),
        ("animacao", [], "azul"),
        ("analise", [(0, 0), (1, 2), (0, 0)], "azul"),
    ],
)
def test_argumentos_invalidos_sao_rejeitados(modo, percurso, cor) -> None:
    with pytest.raises(ValueError):
        app.argumentos_tabuleiro(modo, 5, (0, 0), percurso, cor=cor)


@pytest.mark.parametrize(
    "n, cores",
    [
        (5, ["branco", "branco", "azul", "preto", "preto"]),
        (8, ["branco", "branco", "branco", "azul", "azul", "preto", "preto", "preto"]),
    ],
)
def test_cor_do_cavalo_pela_linha_inicial(n, cores) -> None:
    assert [app.cor_pela_posicao(n, linha) for linha in range(n)] == cores


@pytest.mark.parametrize("linha", [-1, 5])
def test_cor_pela_posicao_rejeita_linha_fora(linha) -> None:
    with pytest.raises(ValueError):
        app.cor_pela_posicao(5, linha)


def test_componente_existe() -> None:
    assert (app.DIR_COMPONENTE / "index.html").is_file()


def test_miniatura_traça_o_percurso() -> None:
    svg = app.gerar_svg_miniatura(5, PERCURSO_PARCIAL_MANUAL)
    assert svg.count("<rect") == 25 + 1
    assert svg.count("<polyline") == 1
    assert app.COR_LATAO in svg


@pytest.mark.parametrize(
    "motivo, completo, trecho",
    [
        ("completo", True, "Passeio completo"),
        ("limite_estados", False, "orçamento acabar"),
        ("busca_esgotada", False, "esgotou"),
        ("sem_movimentos", False, "sem saltos"),
    ],
)
def test_frase_de_conclusao(motivo, completo, trecho) -> None:
    percurso = PASSEIO_5X5_MANUAL if completo else PERCURSO_PARCIAL_MANUAL
    resultado = _resultado_manual(percurso, motivo=motivo)
    assert trecho in app.frase_conclusao(resultado)


# --------------------------------------------------------------------------- painéis


def test_painel_mostra_valores_do_resultado() -> None:
    html = app.gerar_html_painel(_resultado_manual(PERCURSO_PARCIAL_MANUAL))
    assert '<span class="numero">4</span>' in html
    assert "de 25 casas" in html
    assert "16,00%" in html
    assert html.count('class="cheia"') == 4
    assert html.count("<i ") == 25
    assert "Passeio parcial" in html and "sem_movimentos" in html
    assert "Passeio completo impossível" not in html


@pytest.mark.parametrize("paridade", [False, True])
@pytest.mark.parametrize(
    "validacao",
    [None, ResultadoValidacao(True, False), ResultadoValidacao(False, False, ("erro",))],
)
def test_painel_nao_vira_bloco_de_codigo_no_markdown(paridade, validacao) -> None:
    # Regressão: sem aviso de paridade sobrava uma linha vazia seguida de uma linha
    # recuada, e o Markdown mostrava o HTML da conferência como código.
    resultado = _resultado_manual(PERCURSO_PARCIAL_MANUAL, paridade=paridade)
    html = app.gerar_html_painel(resultado, validacao)
    linhas = html.splitlines()
    assert all(linha.strip() for linha in linhas)
    assert not any(linha.startswith(" ") for linha in linhas)


def test_cartoes_nao_viram_bloco_de_codigo() -> None:
    html = app.gerar_html_cartoes_comparacao([_resultado_manual(PERCURSO_PARCIAL_MANUAL)] * 2)
    assert not any(linha.startswith(" ") or not linha.strip() for linha in html.splitlines())


def test_painel_mostra_limite_e_paridade() -> None:
    resultado = _resultado_manual(
        [(0, 1), (2, 0)], modo="recuo", motivo="limite_estados", paridade=True, max_estados=10_000
    )
    html = app.gerar_html_painel(resultado)
    assert "Limite de execução" in html
    assert "Passeio completo impossível por paridade" in html
    assert "24 casas" in html
    assert "10.000" in html


def test_nota_da_proposicao_so_aparece_quando_medida() -> None:
    resultado = _resultado_manual(PERCURSO_PARCIAL_MANUAL)
    assert "Proposição 5.3" not in app.gerar_html_eficiencia(resultado)
    com_nota = replace(resultado, estados_sem_completo_possivel=1234)
    html = app.gerar_html_eficiencia(com_nota)
    assert "1.234" in html and "Proposição 5.3" in html


def test_conferencia_sem_validador_diz_que_nao_rodou(monkeypatch) -> None:
    def pendente(n, inicio, percurso):
        raise NotImplementedError

    monkeypatch.setattr(core.validator, "validar_percurso", pendente)
    resultado = _resultado_manual(PASSEIO_5X5_MANUAL, motivo="completo")
    assert app.conferir_percurso(resultado) is None
    html = app.gerar_html_eficacia(resultado, None)
    assert "ainda não disponível" in html and "conferido" not in html


@pytest.mark.parametrize(
    "validacao, trecho",
    [
        (ResultadoValidacao(True, True), "Passeio completo conferido"),
        (ResultadoValidacao(True, False), "Percurso conferido"),
        (ResultadoValidacao(False, False, ("salto inválido",)), "rejeitou"),
    ],
)
def test_conferencia_mostra_o_veredito_do_validador(monkeypatch, validacao, trecho) -> None:
    recebido = []

    def validar(n, inicio, percurso):
        recebido.append((n, inicio, list(percurso)))
        return validacao

    monkeypatch.setattr(core.validator, "validar_percurso", validar)
    resultado = _resultado_manual(PERCURSO_PARCIAL_MANUAL)
    html = app.gerar_html_eficacia(resultado, app.conferir_percurso(resultado))
    assert trecho in html
    assert recebido == [(5, resultado.config.inicio, PERCURSO_PARCIAL_MANUAL)]


def test_linha_de_resultado_copia_os_valores() -> None:
    resultado = _resultado_manual(PERCURSO_PARCIAL_MANUAL)
    linha = app.resultado_para_linha(resultado)
    assert linha["combinacao"] == "guloso / restritiva"
    assert linha["casas_visitadas"] == 4
    assert linha["verificacoes_movimentos"] == resultado.verificacoes_movimentos


def _csv_ficticio() -> pd.DataFrame:
    linhas = []
    for cenario in ("T01", "T02"):
        for modo in app.MODOS:
            for variante in app.VARIANTES:
                linhas.append({
                    "cenario": cenario, "modo": modo, "variante": variante,
                    "cobertura_percentual": 50.0, "estados_explorados": 10,
                    "verificacoes_movimentos": 100, "tempo_segundos": 0.01,
                })
    return pd.DataFrame(linhas)


def test_grafico_tem_uma_barra_por_combinacao_e_grupo() -> None:
    fig = app.grafico_comparativo(_csv_ficticio(), grupo="cenario")
    assert len(fig.axes) == len(app.METRICAS_GRAFICO)
    assert all(len(eixo.patches) == 2 * 4 for eixo in fig.axes)
    plt.close(fig)


def test_legenda_do_grafico_segue_a_ordem_dos_cartoes() -> None:
    fig = app.grafico_comparativo(_csv_ficticio())
    _, rotulos = fig.axes[0].get_legend_handles_labels()
    assert rotulos == [app.rotulo_combinacao(m, v) for m in app.MODOS for v in app.VARIANTES]
    plt.close(fig)


def _csv_ficticio_completo() -> pd.DataFrame:
    df = _csv_ficticio()
    df["tabuleiro"] = df["cenario"].map({"T01": "5x5", "T02": "8x8"})
    df["posicao_inicial"] = "(1, 1)"
    df["objetivo"] = "Canto"
    df["validador_aprovado"] = [True] * (len(df) - 1) + [False]
    df["versao_codigo"] = "abc1234"
    return df


def test_rotulo_de_cenario_junta_tabuleiro_e_inicio() -> None:
    df = app.rotular_cenarios(_csv_ficticio_completo())
    assert df["rotulo_cenario"].iloc[0] == "T01\n5x5 (1, 1)"
    assert set(df["rotulo_cenario"]) == {"T01\n5x5 (1, 1)", "T02\n8x8 (1, 1)"}


def test_rotulo_de_cenario_sem_colunas_extras_usa_o_codigo() -> None:
    df = app.rotular_cenarios(_csv_ficticio())
    assert set(df["rotulo_cenario"]) == {"T01", "T02"}


def test_resumo_dos_experimentos_le_o_csv() -> None:
    html = app.gerar_html_resumo_experimentos(_csv_ficticio_completo())
    assert "<dd>8</dd>" in html
    assert "7 de 8 aprovadas" in html
    assert "abc1234" in html
    assert "<strong>T02</strong> 8x8, início (1, 1): Canto" in html


def test_resumo_tolera_csv_sem_colunas_opcionais() -> None:
    html = app.gerar_html_resumo_experimentos(_csv_ficticio())
    assert "<dd>8</dd>" in html and "Validador" not in html


def test_grafico_aceita_rotulo_de_cenario() -> None:
    fig = app.grafico_comparativo(app.rotular_cenarios(_csv_ficticio_completo()),
                                  grupo="rotulo_cenario")
    assert [t.get_text() for t in fig.axes[0].get_xticklabels()] == [
        "T01\n5x5 (1, 1)", "T02\n8x8 (1, 1)"]
    plt.close(fig)


def test_experimentos_ausentes_retornam_none(tmp_path: Path) -> None:
    assert app.carregar_experimentos(tmp_path / "nao_existe.csv") is None


def test_experimentos_existentes_sao_lidos(tmp_path: Path) -> None:
    caminho = tmp_path / "experiments.csv"
    _csv_ficticio().to_csv(caminho, index=False)
    assert len(app.carregar_experimentos(caminho)) == 8


# --------------------------------------------------------------------------- página


def _botao(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _html(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def _duble(recebido: list[ConfiguracaoExecucao]):
    def resolver(config):
        recebido.append(config)
        return _resultado_manual(PERCURSO_PARCIAL_MANUAL)
    return resolver


def test_tela_inicial_tem_capa_e_dois_caminhos() -> None:
    at = AppTest.from_file(ARQUIVO_APP).run()
    assert not at.exception
    html = _html(at)
    assert "Passeio do Cavalo" in html and "Estratégia PARE e Análise de Complexidade" in html
    _botao(at, "Sobre o sistema").click().run()
    assert at.session_state["tela"] == "sobre"
    _botao(at, "Iniciar análise").click().run()
    assert at.session_state["tela"] == "configurar"


def test_menu_so_mostra_resultados_depois_da_primeira_analise() -> None:
    at = AppTest.from_file(ARQUIVO_APP).run()
    rotulos = {b.label for b in at.sidebar.button}
    assert "Resultados" not in rotulos and "Experimentos" in rotulos


def test_resolvedor_indisponivel_mantem_na_configuracao(monkeypatch) -> None:
    def pendente(config):
        raise NotImplementedError("F6 pendente")

    monkeypatch.setattr(core.api, "resolver", pendente)
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    _botao(at, "Executar análise").click().run()
    assert not at.exception
    assert at.session_state["tela"] == "configurar"
    assert any("ainda não está disponível" in e.value for e in at.error)


def test_fluxo_completo_ate_resultados_e_novo_teste(monkeypatch) -> None:
    recebido: list[ConfiguracaoExecucao] = []
    monkeypatch.setattr(core.api, "resolver", _duble(recebido))
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    at.radio(key="cfg_n").set_value(5).run()
    at.number_input(key="cfg_coluna").set_value(3).run()
    _botao(at, "Executar análise").click().run()

    assert not at.exception
    assert recebido[0] == ConfiguracaoExecucao(n=5, inicio=(0, 2), modo="guloso",
                                               variante="restritiva", seed=app.SEED_PADRAO)
    assert at.session_state["tela"] == "percurso"

    _botao(at, "Pular para os resultados ⏭").click().run()
    assert at.session_state["tela"] == "resultados"
    html = _html(at)
    assert "O cavalo visitou 4 de 25 casas" in html
    assert "16,00%" in html and "Eficiência" in html

    _botao(at, "Novo teste").click().run()
    assert at.session_state["tela"] == "configurar"
    assert at.session_state["cfg_n"] == 5 and at.session_state["cfg_coluna"] == 3


def test_linha_e_coluna_sao_limitadas_ao_trocar_para_5x5() -> None:
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    at.number_input(key="cfg_linha").set_value(8).run()
    at.radio(key="cfg_n").set_value(5).run()
    assert not at.exception
    assert at.session_state["cfg_linha"] == 5


def test_comparacao_roda_as_quatro_combinacoes(monkeypatch) -> None:
    recebido: list[ConfiguracaoExecucao] = []
    monkeypatch.setattr(core.api, "resolver", _duble(recebido))
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    _botao(at, "Executar análise").click().run()
    _botao(at, "Pular para os resultados ⏭").click().run()
    _botao(at, "Comparar as 4 combinações").click().run()

    assert not at.exception
    comparadas = recebido[1:]
    assert {(c.modo, c.variante) for c in comparadas} == {
        (m, v) for m in app.MODOS for v in app.VARIANTES
    }
    assert all(c.inicio == recebido[0].inicio for c in comparadas)
    assert all(c.max_estados == app.MAX_ESTADOS_PADRAO for c in comparadas if c.modo == "recuo")
    assert _html(at).count('<figure class="cartao">') == 4


def test_mensagens_de_erro_do_resolvedor() -> None:
    cfg = ConfiguracaoExecucao(n=5, inicio=(0, 0), modo="recuo", max_estados=10)
    assert "modo “Com recuo limitado” ainda não está disponível" in app.mensagem_de_erro(
        cfg, NotImplementedError())
    assert "recusou a configuração: x" in app.mensagem_de_erro(cfg, ValueError("x"))
    assert "não passou na conferência" in app.mensagem_de_erro(cfg, RuntimeError("y"))


def test_erro_interno_do_resolvedor_nao_derruba_a_tela(monkeypatch) -> None:
    def quebrado(config):
        raise RuntimeError("Percurso inválido produzido pelo resolvedor")

    monkeypatch.setattr(core.api, "resolver", quebrado)
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    _botao(at, "Executar análise").click().run()
    assert not at.exception
    assert at.session_state["tela"] == "configurar"
    assert any("conferência interna" in e.value for e in at.error)


def test_comparacao_mostra_so_as_combinacoes_disponiveis(monkeypatch) -> None:
    recebido: list[ConfiguracaoExecucao] = []
    duble = _duble(recebido)

    def sem_recuo(config):
        if config.modo == "recuo":
            raise NotImplementedError
        return duble(config)

    monkeypatch.setattr(core.api, "resolver", sem_recuo)
    at = AppTest.from_file(ARQUIVO_APP).run()
    _botao(at, "Iniciar análise").click().run()
    _botao(at, "Executar análise").click().run()
    _botao(at, "Pular para os resultados ⏭").click().run()
    _botao(at, "Comparar as 4 combinações").click().run()

    assert not at.exception and not at.error
    html = _html(at)
    assert html.count('<figure class="cartao">') == 2
    assert "Comparação de 2 combinações" in html
    assert any("recuo / restritiva" in i.value and "recuo / expansiva" in i.value
               for i in at.info)


def test_menu_lateral_comeca_recolhido() -> None:
    at = AppTest.from_file(ARQUIVO_APP).run()
    assert not at.exception
    assert 'initial_sidebar_state="collapsed"' in Path(ARQUIVO_APP).read_text(encoding="utf-8")


def test_nao_ha_mais_seletor_de_cor() -> None:
    at = AppTest.from_file(ARQUIVO_APP).run()
    assert "cor_cavalo" not in at.session_state
