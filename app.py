"""Interface Streamlit do Passeio do Cavalo — Estratégia PARE.

Execute com::

    streamlit run app.py

Identidade visual: uma súmula de torneio de xadrez impressa em tinta azul-marinho,
com acento em latão. O tema base (cores e fontes) está em ``.streamlit/config.toml``
e o tabuleiro animado é o componente ``componentes/tabuleiro/index.html``.

Fluxo de telas: início -> (sobre) -> configurar -> percurso animado -> resultados.
O menu lateral leva a qualquer tela depois da primeira análise.

Regras seguidas (AGENTS.md):
- toda execução passa por ``core.api.resolver``; a interface não chama ``pare.py``
  nem ``busca.py`` diretamente;
- coordenadas são 1-based na tela e convertidas para 0-based apenas aqui;
- o tabuleiro mostra **somente** o melhor percurso devolvido, nunca a ordem de
  exploração da busca;
- nenhum número é gerado pela interface: métricas vêm do ``ResultadoExecucao`` e
  a aba de experimentos apenas lê ``results/experiments.csv``.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

import core.api  # noqa: E402
import core.validator  # noqa: E402
from core.render import construir_matriz_visitas, descrever_motivo_parada  # noqa: E402
from core.tipos import (  # noqa: E402
    DIMENSOES_OBRIGATORIAS,
    ConfiguracaoExecucao,
    Posicao,
    ResultadoExecucao,
    ResultadoValidacao,
)

TITULO = "Passeio do Cavalo — Estratégia PARE e Análise de Complexidade"
CAMINHO_EXPERIMENTOS = Path(__file__).resolve().parent / "results" / "experiments.csv"
MAX_ESTADOS_PADRAO = 10_000
SEED_PADRAO = 2026

# Paleta (mesmos valores de .streamlit/config.toml).
COR_TINTA = "#1C2559"
COR_TINTA_SUAVE = "#4A5486"
COR_LINHA = "#D5DAE5"
COR_LATAO = "#C08A1E"
COR_CLARA = "#E4E8F0"
COR_ESCURA = "#9AA6BF"

MODOS = ("guloso", "recuo")
VARIANTES = ("restritiva", "expansiva")
ROTULO_MODO = {"guloso": "Guloso (sem recuo)", "recuo": "Com recuo limitado"}
ROTULO_VARIANTE = {
    "restritiva": "Restritiva (principal), menor A",
    "expansiva": "Expansiva (comparação), maior A",
}
# Restritiva em tinta, expansiva em latão; tom claro = guloso, escuro = recuo.
COR_COMBINACAO = {
    ("guloso", "restritiva"): "#8B93C4",
    ("recuo", "restritiva"): COR_TINTA,
    ("guloso", "expansiva"): "#E2C27A",
    ("recuo", "expansiva"): COR_LATAO,
}
METRICAS_GRAFICO = (
    ("cobertura_percentual", "Cobertura (%)", False),
    ("estados_explorados", "Estados explorados (escala log)", True),
    ("verificacoes_movimentos", "Verificações de movimentos (escala log)", True),
    ("tempo_segundos", "Tempo de resolução em s (escala log)", True),
)


# --------------------------------------------------------------------------- formatação


def formatar_inteiro(valor: int) -> str:
    """Inteiro com separador de milhar brasileiro (``10000`` -> ``10.000``)."""
    return f"{valor:,}".replace(",", ".")


def formatar_decimal(valor: float, casas: int = 2) -> str:
    """Decimal no padrão brasileiro (``1234.5`` -> ``1.234,50``)."""
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_casa(posicao: Posicao) -> str:
    """Casa 0-based exibida como ``(linha, coluna)`` 1-based."""
    return f"({posicao[0] + 1}, {posicao[1] + 1})"


def rotulo_combinacao(modo: str, variante: str) -> str:
    """Nome curto de uma combinação modo/variante para tabelas e legendas."""
    return f"{modo} / {variante}"


# --------------------------------------------------------------------------- configuração


def construir_configuracao(
    n: int,
    linha: int,
    coluna: int,
    modo: str,
    variante: str,
    seed: int | None,
    max_estados: int | None,
) -> ConfiguracaoExecucao:
    """Converte a entrada 1-based da tela em ``ConfiguracaoExecucao`` 0-based.

    Raises:
        ValueError: Se a dimensão, a posição ou o orçamento forem inválidos.
    """
    if n not in DIMENSOES_OBRIGATORIAS:
        raise ValueError(f"Dimensão {n} não suportada; use {DIMENSOES_OBRIGATORIAS}.")
    for nome, valor in (("Linha", linha), ("Coluna", coluna)):
        if not 1 <= valor <= n:
            raise ValueError(f"{nome} deve estar entre 1 e {n}; recebido {valor}.")
    if modo == "recuo":
        if max_estados is None or max_estados <= 0:
            raise ValueError("No modo com recuo, max_estados deve ser um inteiro positivo.")
    else:
        max_estados = None
    return ConfiguracaoExecucao(
        n=n,
        inicio=(linha - 1, coluna - 1),
        modo=modo,
        variante=variante,
        seed=seed,
        max_estados=max_estados,
    )


# --------------------------------------------------------------------------- tabuleiro

DIR_COMPONENTE = Path(__file__).resolve().parent / "componentes" / "tabuleiro"
MODOS_TABULEIRO = ("previa", "animacao", "analise")
CORES_CAVALO = {"azul": "Azul", "preto": "Preto", "branco": "Branco"}

_componente_tabuleiro = components.declare_component("tabuleiro_pare", path=str(DIR_COMPONENTE))


def cor_pela_posicao(n: int, linha: int) -> str:
    """Cor do cavalo definida pela linha inicial (0-based).

    Linhas de cima: ``"branco"``; linhas de baixo: ``"preto"``; faixa do meio:
    ``"azul"``. Com ``n`` ímpar o meio é a linha central (5×5: 1–2 branco, 3 azul,
    4–5 preto, em 1-based); com ``n`` par são as duas linhas centrais (8×8: 1–3
    branco, 4–5 azul, 6–8 preto). É só identidade visual: não altera a busca.

    Raises:
        ValueError: Se ``linha`` estiver fora do tabuleiro.
    """
    if not 0 <= linha < n:
        raise ValueError(f"Linha {linha} fora do tabuleiro {n}×{n}.")
    meio_inicio, meio_fim = (n - 1) // 2, n // 2
    if linha < meio_inicio:
        return "branco"
    if linha > meio_fim:
        return "preto"
    return "azul"


def argumentos_tabuleiro(
    modo: str,
    n: int,
    inicio: Posicao,
    percurso: Sequence[Posicao] = (),
    cor: str = "azul",
    execucao: int = 0,
) -> dict:
    """Monta os argumentos do componente do tabuleiro (``componentes/tabuleiro``).

    O percurso é validado por ``core.render.construir_matriz_visitas`` (limites e
    unicidade). O componente só desenha o percurso recebido: na animação ele
    reproduz o **melhor percurso** já calculado, nunca a ordem de exploração.

    Raises:
        ValueError: Se o modo, a cor ou o percurso forem inválidos.
    """
    if modo not in MODOS_TABULEIRO:
        raise ValueError(f"Modo de tabuleiro desconhecido: {modo!r}.")
    if cor not in CORES_CAVALO:
        raise ValueError(f"Cor de cavalo desconhecida: {cor!r}.")
    construir_matriz_visitas(n, percurso)
    if modo != "previa" and not percurso:
        raise ValueError("A animação e a análise precisam de um percurso.")
    return {
        "modo": modo,
        "n": n,
        "inicio": list(inicio),
        "percurso": [list(p) for p in percurso],
        "cor": cor,
        "execucao": execucao,
    }


def desenhar_tabuleiro(argumentos: dict, chave: str) -> dict | None:
    """Renderiza o componente; devolve ``{"evento": "fim", ...}`` ao fim da animação."""
    return _componente_tabuleiro(**argumentos, key=chave, default=None)


def frase_conclusao(resultado: ResultadoExecucao) -> str:
    """Frase curta que resume o resultado na tela de resultados."""
    k, v = resultado.casas_visitadas, resultado.total_casas
    if resultado.passeio_completo:
        return f"Passeio completo: o cavalo visitou as {v} casas."
    if resultado.motivo_parada == "limite_estados":
        return f"O cavalo visitou {k} de {v} casas antes de o orçamento acabar."
    if resultado.motivo_parada == "busca_esgotada":
        return f"O cavalo visitou {k} de {v} casas, e a busca esgotou as alternativas."
    return f"O cavalo visitou {k} de {v} casas e ficou sem saltos disponíveis."


def gerar_svg_miniatura(n: int, percurso: Sequence[Posicao], lado: int = 168) -> str:
    """Tabuleiro estático pequeno com o percurso traçado (para comparações)."""
    construir_matriz_visitas(n, percurso)
    c = lado / n
    partes = [f'<svg viewBox="0 0 {lado} {lado}" width="100%" role="img" '
              f'aria-label="Percurso em miniatura">']
    for i in range(n):
        for j in range(n):
            cor = COR_ESCURA if (i + j) % 2 else COR_CLARA
            partes.append(f'<rect x="{j * c:.1f}" y="{i * c:.1f}" width="{c:.1f}" '
                          f'height="{c:.1f}" fill="{cor}"/>')
    centros = [(p[1] * c + c / 2, p[0] * c + c / 2) for p in percurso]
    if len(centros) > 1:
        pontos = " ".join(f"{x:.1f},{y:.1f}" for x, y in centros)
        partes.append(f'<polyline points="{pontos}" fill="none" stroke="{COR_TINTA}" '
                      f'stroke-width="1.6" stroke-linejoin="round" opacity="0.8"/>')
    if centros:
        (x0, y0), (x1, y1) = centros[0], centros[-1]
        partes.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{c * 0.22:.1f}" fill="{COR_TINTA}"/>')
        partes.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="{c * 0.22:.1f}" fill="{COR_LATAO}"/>')
    partes.append(f'<rect x="0" y="0" width="{lado}" height="{lado}" fill="none" '
                  f'stroke="{COR_TINTA}" stroke-width="1.5"/></svg>')
    return "".join(partes)


# --------------------------------------------------------------------------- painéis


def conferir_percurso(resultado: ResultadoExecucao) -> ResultadoValidacao | None:
    """Passa o melhor percurso pelo validador independente; ``None`` se ele não existir ainda."""
    try:
        return core.validator.validar_percurso(
            resultado.config.n, resultado.config.inicio, resultado.melhor_percurso
        )
    except NotImplementedError:
        return None


def _html_conferencia(validacao: ResultadoValidacao | None) -> str:
    if validacao is None:
        return '<p class="conferencia">Validador independente ainda não disponível nesta versão.</p>'
    if validacao.valido:
        texto = ("Passeio completo conferido" if validacao.passeio_completo
                 else "Percurso conferido")
        return f'<p class="conferencia ok">✓ {texto} pelo validador independente.</p>'
    erros = "".join(f"<li>{escape(e)}</li>" for e in validacao.erros)
    return ('<p class="aviso"><strong>O validador independente rejeitou o percurso.</strong></p>'
            f'<ul class="erros">{erros}</ul>')


def gerar_html_eficacia(
    resultado: ResultadoExecucao, validacao: ResultadoValidacao | None = None
) -> str:
    """Painel de eficácia e dados da execução (valores reais do resultado)."""
    cfg = resultado.config
    v, k = resultado.total_casas, resultado.casas_visitadas
    trilha = "".join(f'<i class="{"cheia" if i < k else ""}"></i>' for i in range(v))
    if resultado.passeio_completo:
        selo = '<span class="selo selo-ok">Passeio completo</span>'
    elif resultado.motivo_parada == "limite_estados":
        selo = '<span class="selo selo-limite">Limite de execução</span>'
    else:
        selo = '<span class="selo selo-parcial">Passeio parcial</span>'

    paridade = ""
    if resultado.impossibilidade_paridade:
        paridade = (
            '<p class="aviso"><strong>Passeio completo impossível por paridade.</strong> '
            "A casa inicial é da cor que aparece menos num tabuleiro de lado ímpar, e o "
            f"cavalo troca de cor a cada salto. O máximo teórico é {v - 1} casas. "
            "A busca não foi alterada.</p>"
        )

    orcamento = "não se aplica" if cfg.max_estados is None else formatar_inteiro(cfg.max_estados)
    return f"""
<div class="painel">
  <section class="ficha">
    <h3>Eficácia</h3>
    <div class="cobertura">
      <div class="trilha" style="--n:{cfg.n}" aria-label="{k} de {v} casas visitadas">{trilha}</div>
      <div>
        <span class="numero">{k}</span><span class="de">de {v} casas</span>
        <div class="pct">cobertura de {formatar_decimal(resultado.cobertura_percentual)}%</div>
      </div>
    </div>
    <div class="parada">{selo}<span>{escape(descrever_motivo_parada(resultado.motivo_parada))}
      <code>{escape(resultado.motivo_parada)}</code></span></div>
    {paridade}
    {_html_conferencia(validacao)}
  </section>
  <dl class="execucao">
    <dt>Tabuleiro</dt><dd>{cfg.n}×{cfg.n}, início {formatar_casa(cfg.inicio)}</dd>
    <dt>Estratégia</dt><dd>{escape(ROTULO_MODO[cfg.modo])}, variante {escape(cfg.variante)}</dd>
    <dt>Semente</dt><dd>{resultado.seed_utilizada}</dd>
    <dt>Orçamento</dt><dd>{orcamento}</dd>
    <dt>Código</dt><dd><code>{escape(resultado.versao_codigo)}</code></dd>
  </dl>
</div>
"""


def gerar_html_eficiencia(resultado: ResultadoExecucao) -> str:
    """Faixa de eficiência: as métricas de esforço medidas durante a resolução."""
    itens = (
        ("Verificações de movimentos", formatar_inteiro(resultado.verificacoes_movimentos),
         "Entradas lidas de listas de adjacência durante a resolução. "
         "É a principal métrica de esforço."),
        ("Estados explorados", formatar_inteiro(resultado.estados_explorados),
         "Entradas em caminhos parciais válidos, incluindo a casa inicial."),
        ("Avaliações de candidatos", formatar_inteiro(resultado.avaliacoes_candidatos),
         "Cálculos da chave (F, I, P, A)."),
        ("Recuos", formatar_inteiro(resultado.recuos),
         "Casas removidas do caminho ao voltar atrás. Sempre zero no guloso."),
        ("Tempo de resolução", f"{formatar_decimal(resultado.tempo_segundos, 6)} s",
         "Só a busca, medida com time.perf_counter(). Varia com a máquina."),
        ("Verificações de preparo", formatar_inteiro(resultado.verificacoes_preparo),
         "Deslocamentos testados ao montar as adjacências, contados à parte."),
    )
    celulas = "".join(
        f'<div class="item"><span class="rotulo">{rotulo}</span>'
        f'<span class="valor">{valor}</span><small>{explicacao}</small></div>'
        for rotulo, valor, explicacao in itens
    )
    nota = ""
    if resultado.estados_sem_completo_possivel > 0:
        nota = (
            f'<p class="nota">{formatar_inteiro(resultado.estados_sem_completo_possivel)} '
            "estados foram expandidos quando a condição necessária da Proposição 5.3 "
            "(F = 1, I = 0, P ≤ 1) já indicava que o passeio completo não era mais possível. "
            "O indicador é só informativo: nenhum candidato foi descartado por ele.</p>"
        )
    return (f'<section class="ficha"><h3>Eficiência</h3><div class="livro">{celulas}</div>'
            f"{nota}</section>")


def gerar_html_painel(
    resultado: ResultadoExecucao, validacao: ResultadoValidacao | None = None
) -> str:
    """Eficácia e eficiência juntas (valores reais do resultado)."""
    return gerar_html_eficacia(resultado, validacao) + gerar_html_eficiencia(resultado)


def resultado_para_linha(resultado: ResultadoExecucao) -> dict[str, object]:
    """Converte um ``ResultadoExecucao`` em uma linha de tabela (valores reais)."""
    cfg = resultado.config
    return {
        "combinacao": rotulo_combinacao(cfg.modo, cfg.variante),
        "modo": cfg.modo,
        "variante": cfg.variante,
        "casas_visitadas": resultado.casas_visitadas,
        "cobertura_percentual": resultado.cobertura_percentual,
        "passeio_completo": resultado.passeio_completo,
        "motivo_parada": resultado.motivo_parada,
        "tempo_segundos": resultado.tempo_segundos,
        "estados_explorados": resultado.estados_explorados,
        "verificacoes_movimentos": resultado.verificacoes_movimentos,
        "avaliacoes_candidatos": resultado.avaliacoes_candidatos,
        "recuos": resultado.recuos,
    }


def gerar_html_cartoes_comparacao(resultados: Sequence[ResultadoExecucao]) -> str:
    """Quatro cartões lado a lado, cada um com o percurso em miniatura."""
    cartoes = []
    for r in resultados:
        cfg = r.config
        cor = COR_COMBINACAO[(cfg.modo, cfg.variante)]
        cartoes.append(f"""
<figure class="cartao">
  <figcaption><i style="background:{cor}"></i>{escape(rotulo_combinacao(cfg.modo, cfg.variante))}</figcaption>
  {gerar_svg_miniatura(cfg.n, r.melhor_percurso)}
  <p><strong>{r.casas_visitadas}/{r.total_casas}</strong> casas<br>
  {formatar_inteiro(r.estados_explorados)} estados<br>
  {formatar_inteiro(r.verificacoes_movimentos)} verificações</p>
</figure>""")
    return f'<div class="cartoes">{"".join(cartoes)}</div>'


# --------------------------------------------------------------------------- gráficos


def grafico_comparativo(df: pd.DataFrame, grupo: str | None = None) -> plt.Figure:
    """Gráficos de barras agrupadas: uma barra por combinação modo/variante.

    Args:
        df: Tabela com as colunas ``modo``, ``variante`` e as de ``METRICAS_GRAFICO``.
        grupo: Coluna que separa grupos no eixo x (por exemplo, ``"cenario"``);
            ``None`` para um único grupo.
    """
    grupos = [None] if grupo is None else list(dict.fromkeys(df[grupo]))
    combinacoes = [(m, v) for v in VARIANTES for m in MODOS]
    largura = 0.8 / len(combinacoes)

    fig, eixos = plt.subplots(1, len(METRICAS_GRAFICO), figsize=(13, 3.3))
    fig.patch.set_alpha(0)
    for eixo, (coluna, titulo, log) in zip(eixos, METRICAS_GRAFICO):
        for i, (modo, variante) in enumerate(combinacoes):
            alturas = []
            for g in grupos:
                filtro = (df["modo"] == modo) & (df["variante"] == variante)
                if g is not None:
                    filtro &= df[grupo] == g
                valores = df.loc[filtro, coluna]
                alturas.append(float(valores.iloc[0]) if len(valores) else float("nan"))
            posicoes = [x + (i - (len(combinacoes) - 1) / 2) * largura for x in range(len(grupos))]
            eixo.bar(posicoes, alturas, width=largura, color=COR_COMBINACAO[(modo, variante)],
                     label=rotulo_combinacao(modo, variante))
        if log and (df[coluna] > 0).all():
            eixo.set_yscale("log")
        else:
            titulo = titulo.replace(" (escala log)", "")
        eixo.set_title(titulo, fontsize=10, color=COR_TINTA, loc="left")
        eixo.set_xticks(range(len(grupos)))
        eixo.set_xticklabels(["" if g is None else str(g) for g in grupos])
        eixo.set_facecolor("none")
        eixo.grid(axis="y", color=COR_LINHA, linewidth=0.8)
        eixo.set_axisbelow(True)
        for lado in ("top", "right", "left"):
            eixo.spines[lado].set_visible(False)
        eixo.spines["bottom"].set_color(COR_TINTA)
        eixo.tick_params(colors=COR_TINTA_SUAVE, labelsize=9, length=0)
    alcas, rotulos = eixos[0].get_legend_handles_labels()
    fig.legend(alcas, rotulos, loc="upper center", ncol=len(combinacoes), frameon=False,
               fontsize=9, labelcolor=COR_TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return fig


def carregar_experimentos(caminho: Path = CAMINHO_EXPERIMENTOS) -> pd.DataFrame | None:
    """Lê o CSV de experimentos gerado por ``run_experiments.py``; ``None`` se não existir."""
    if not caminho.is_file():
        return None
    return pd.read_csv(caminho)


COLUNAS_TABELA_EXPERIMENTOS = (
    "cenario", "tabuleiro", "posicao_inicial", "modo", "variante", "casas_visitadas",
    "total_casas", "cobertura_percentual", "passeio_completo", "motivo_parada",
    "estados_explorados", "verificacoes_movimentos", "avaliacoes_candidatos", "recuos",
    "tempo_segundos", "validador_aprovado",
)
CONFIG_COLUNAS_EXPERIMENTOS = {
    "cenario": "Cenário",
    "tabuleiro": "Tabuleiro",
    "posicao_inicial": "Início",
    "modo": "Modo",
    "variante": "Variante",
    "casas_visitadas": "Casas",
    "total_casas": "Total",
    "cobertura_percentual": st.column_config.NumberColumn("Cobertura %", format="%.2f"),
    "passeio_completo": "Completo?",
    "motivo_parada": "Motivo",
    "estados_explorados": "Estados",
    "verificacoes_movimentos": "Verificações",
    "avaliacoes_candidatos": "Avaliações",
    "recuos": "Recuos",
    "tempo_segundos": st.column_config.NumberColumn("Tempo (s)", format="%.6f"),
    "validador_aprovado": "Validador",
}


def rotular_cenarios(df: pd.DataFrame) -> pd.DataFrame:
    """Copia ``df`` com a coluna ``rotulo_cenario`` (ex.: ``"T01\\n5x5 (1, 1)"``) para os gráficos."""
    df = df.copy()
    if {"cenario", "tabuleiro", "posicao_inicial"} <= set(df.columns):
        df["rotulo_cenario"] = (df["cenario"].astype(str) + "\n" + df["tabuleiro"].astype(str)
                                + " " + df["posicao_inicial"].astype(str))
    elif "cenario" in df.columns:
        df["rotulo_cenario"] = df["cenario"].astype(str)
    else:
        df["rotulo_cenario"] = ""
    return df


def gerar_html_resumo_experimentos(df: pd.DataFrame) -> str:
    """Resumo lido do CSV: execuções, aprovação no validador, versão do código e cenários."""
    itens = [f"<dt>Execuções</dt><dd>{len(df)}</dd>"]
    if "validador_aprovado" in df.columns:
        aprovadas = int(df["validador_aprovado"].astype(str).str.lower().eq("true").sum())
        itens.append(f"<dt>Validador</dt><dd>{aprovadas} de {len(df)} aprovadas</dd>")
    if "versao_codigo" in df.columns:
        versoes = ", ".join(escape(str(v)) for v in dict.fromkeys(df["versao_codigo"]))
        itens.append(f"<dt>Código</dt><dd><code>{versoes}</code></dd>")
    if {"cenario", "tabuleiro", "posicao_inicial"} <= set(df.columns):
        cenarios = df.drop_duplicates("cenario")
        linhas = []
        for _, c in cenarios.iterrows():
            objetivo = f": {escape(str(c['objetivo']))}" if "objetivo" in df.columns else ""
            linhas.append(f"<strong>{escape(str(c['cenario']))}</strong> {escape(str(c['tabuleiro']))}, "
                          f"início {escape(str(c['posicao_inicial']))}{objetivo}")
        itens.append(f"<dt>Cenários</dt><dd>{'<br>'.join(linhas)}</dd>")
    return f'<dl class="execucao resumo-exp">{"".join(itens)}</dl>'


# --------------------------------------------------------------------------- estilo

CSS_GLOBAL = """
<style>
.block-container { padding-top: 2.2rem; max-width: 1240px; }
.painel { display: flex; flex-direction: column; gap: 14px; }
.ficha { background: #fff; border: 1px solid #D5DAE5; border-radius: 8px; padding: 16px 18px; }
.ficha h3 {
  font-family: "Spectral", Georgia, serif; font-size: 1.15rem; font-weight: 600;
  margin: 0 0 10px; padding: 0; color: #1C2559;
}
.ficha-vazia p { margin: 0; color: #4A5486; font-size: .92rem; line-height: 1.55; }
.cobertura { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 18px; margin-bottom: 14px; }
.cobertura .numero { font-family: "Spectral", Georgia, serif; font-size: 3rem; font-weight: 600; line-height: 1; margin-right: 6px; }
.cobertura .de { color: #4A5486; }
.cobertura .pct { margin-top: 6px; font-size: .88rem; color: #4A5486; font-variant-numeric: tabular-nums; }
.trilha { flex: none; display: grid; grid-template-columns: repeat(var(--n), 9px); gap: 2px; }
.trilha i { width: 9px; height: 9px; background: #E4E8F0; border-radius: 2px; }
.trilha i.cheia { background: #1C2559; }
.parada { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; font-size: .88rem; color: #4A5486; line-height: 1.45; }
.parada code { font-size: .78rem; }
.selo { flex: none; padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600; white-space: nowrap; }
.selo-ok { background: #1C2559; color: #fff; }
.selo-parcial { background: #E4E8F0; color: #1C2559; }
.selo-limite { background: #f3e6c6; color: #7a5410; }
.aviso { margin: 12px 0 0; padding: 10px 12px; border-left: 3px solid #C08A1E; background: #faf4e6;
         font-size: .85rem; line-height: 1.5; color: #4a3a12; }
.livro { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; }
.livro .item { padding: 12px 18px 12px 0; display: flex; flex-direction: column; gap: 2px; }
.livro .item:nth-child(n+4) { border-top: 1px solid #E4E8F0; }
.livro .rotulo { font-size: .85rem; color: #4A5486; }
.livro .valor { font-family: "Spectral", Georgia, serif; font-size: 1.7rem; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; }
.livro small { font-size: .76rem; color: #6b7393; line-height: 1.4; }
@media (max-width: 900px) { .livro { grid-template-columns: repeat(2, minmax(0, 1fr)); } .livro .item:nth-child(n+3) { border-top: 1px solid #E4E8F0; } }
.execucao { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; margin: 0 4px; font-size: .85rem; }
.execucao dt { color: #6b7393; }
.execucao dd { margin: 0; color: #1C2559; }
.resumo-exp { margin: 0 0 1rem; line-height: 1.5; }
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin: 8px 0 18px; }
.cartao { margin: 0; background: #fff; border: 1px solid #D5DAE5; border-radius: 8px; padding: 12px; }
.cartao figcaption { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: .88rem; margin-bottom: 10px; }
.cartao figcaption i { width: 12px; height: 12px; border-radius: 3px; }
.cartao p { margin: 10px 0 0; font-size: .84rem; line-height: 1.5; color: #4A5486; font-variant-numeric: tabular-nums; }
.cartao p strong { color: #1C2559; }
.marca { flex: none; border-radius: 50%; background: #1C2559; color: #fff; display: grid; place-items: center; line-height: 1;
  box-shadow: inset 0 0 0 3px #1C2559, inset 0 0 0 5px #C08A1E; }
.capa { text-align: center; padding: 6vh 0 2rem; }
.capa .marca { width: 112px; height: 112px; font-size: 70px; margin: 0 auto 1.6rem;
  box-shadow: inset 0 0 0 5px #1C2559, inset 0 0 0 8px #C08A1E; }
.capa h1 { font-family: "Spectral", Georgia, serif; font-size: 3.4rem; font-weight: 600; line-height: 1.05;
  color: #1C2559; margin: 0; padding: 0; letter-spacing: -.015em; }
.capa .subtitulo { font-family: "Spectral", Georgia, serif; font-size: 1.35rem; color: #4A5486; margin: .5rem 0 1.4rem; }
.capa .resumo { max-width: 34rem; margin: 0 auto; font-size: 1rem; line-height: 1.65; color: #4A5486; }
.capa .rodape { margin-top: 2.2rem; font-size: .82rem; color: #6b7393; line-height: 1.6; }
.topo { display: flex; gap: 14px; align-items: center; }
.topo .marca { width: 40px; height: 40px; font-size: 24px; box-shadow: inset 0 0 0 2px #1C2559, inset 0 0 0 4px #C08A1E; }
.topo .nome { font-family: "Spectral", Georgia, serif; font-size: 1.2rem; font-weight: 600; color: #1C2559; line-height: 1.1; }
.topo .nome span { display: block; font-family: "IBM Plex Sans", sans-serif; font-size: .78rem; font-weight: 400; color: #4A5486; }
.titulo-tela { font-family: "Spectral", Georgia, serif; font-size: 2rem; font-weight: 600; color: #1C2559; margin: 1.2rem 0 .2rem; line-height: 1.15; }
.apoio-tela { color: #4A5486; margin: 0 0 1.2rem; font-size: .95rem; }
.conclusao { font-family: "Spectral", Georgia, serif; font-size: 2.1rem; font-weight: 600; color: #1C2559; margin: 1.2rem 0 .3rem; line-height: 1.15; max-width: 40ch; }
section[data-testid="stSidebar"] .menu-marca { display: flex; gap: 12px; align-items: center; margin: .2rem 0 1.4rem; }
section[data-testid="stSidebar"] .menu-marca .marca { width: 36px; height: 36px; font-size: 22px; background: #E9ECF5; color: #1C2559;
  box-shadow: inset 0 0 0 2px #E9ECF5, inset 0 0 0 4px #C08A1E; }
section[data-testid="stSidebar"] .menu-marca span { font-family: "Spectral", Georgia, serif; font-size: 1.2rem; font-weight: 600; line-height: 1.1; }
.conferencia { margin: 12px 0 0; font-size: .84rem; color: #6b7393; }
.conferencia.ok { color: #1C2559; font-weight: 600; }
.erros { margin: 6px 0 0 1.1rem; font-size: .82rem; color: #4a3a12; }
.ficha .nota { margin: 12px 0 0; padding-top: 10px; border-top: 1px solid #E4E8F0; font-size: .82rem; color: #4A5486; line-height: 1.5; }
section[data-testid="stSidebar"] .menu-rodape { margin-top: 1.6rem; font-size: .75rem; opacity: .7; line-height: 1.5; }
</style>
"""

TELAS = {
    "inicio": "Início",
    "configurar": "Nova análise",
    "resultados": "Resultados",
    "experimentos": "Experimentos",
    "sobre": "Sobre o sistema",
}
CHAVES_CONFIGURACAO = (
    "cfg_n", "cfg_linha", "cfg_coluna", "cfg_modo", "cfg_variante",
    "cfg_orcamento", "cfg_seed_fixa", "cfg_seed",
)
VALORES_PADRAO = {
    "cfg_n": 8, "cfg_linha": 1, "cfg_coluna": 1, "cfg_modo": "guloso",
    "cfg_variante": "restritiva", "cfg_orcamento": MAX_ESTADOS_PADRAO,
    "cfg_seed_fixa": True, "cfg_seed": SEED_PADRAO,
}


# --------------------------------------------------------------------------- estado


def _inicializar_estado() -> None:
    st.session_state.setdefault("tela", "inicio")
    st.session_state.setdefault("resultado", None)
    st.session_state.setdefault("comparacao", None)
    st.session_state.setdefault("erro", None)
    st.session_state.setdefault("execucao", 0)
    for chave, valor in VALORES_PADRAO.items():
        st.session_state.setdefault(chave, valor)
    # O Streamlit descarta o estado de widgets que não aparecem na tela atual.
    # Reatribuir as chaves mantém a configuração ao navegar entre as telas.
    for chave in CHAVES_CONFIGURACAO:
        st.session_state[chave] = st.session_state[chave]


def _ir(tela: str) -> None:
    st.session_state["tela"] = tela
    st.session_state["erro"] = None


def argumentos_formulario() -> dict:
    """Valores atuais do formulário de configuração (1-based, como na tela)."""
    s = st.session_state
    return {
        "n": int(s["cfg_n"]),
        "linha": int(s["cfg_linha"]),
        "coluna": int(s["cfg_coluna"]),
        "modo": s["cfg_modo"],
        "variante": s["cfg_variante"],
        "seed": int(s["cfg_seed"]) if s["cfg_seed_fixa"] else None,
        "max_estados": int(s["cfg_orcamento"]),
    }


def mensagem_de_erro(config: ConfiguracaoExecucao, erro: Exception) -> str:
    """Texto mostrado na tela quando ``core.api.resolver`` não devolve resultado."""
    if isinstance(erro, NotImplementedError):
        return (f"O modo “{ROTULO_MODO[config.modo]}” ainda não está disponível nesta versão "
                "do código. Escolha outro modo ou aguarde a integração.")
    if isinstance(erro, ValueError):
        return f"O algoritmo recusou a configuração: {erro}"
    return ("O algoritmo produziu um resultado que não passou na conferência interna, "
            f"e por isso ele não é exibido. Detalhe: {erro}")


def _chamar_resolver(config: ConfiguracaoExecucao) -> ResultadoExecucao | None:
    try:
        return core.api.resolver(config)
    except (NotImplementedError, ValueError, RuntimeError) as erro:
        st.session_state["erro"] = mensagem_de_erro(config, erro)
    return None


def _executar() -> None:
    st.session_state["erro"] = None
    try:
        config = construir_configuracao(**argumentos_formulario())
    except ValueError as erro:
        st.session_state["erro"] = f"Entrada inválida: {erro}"
        return
    resultado = _chamar_resolver(config)
    if resultado is None:
        return
    st.session_state["resultado"] = resultado
    st.session_state["comparacao"] = None
    st.session_state["execucao"] += 1
    st.session_state["tela"] = "percurso"


def _rever_animacao() -> None:
    st.session_state["execucao"] += 1
    st.session_state["tela"] = "percurso"


def _comparar() -> None:
    """Roda as 4 combinações na mesma posição, semente e orçamento da última análise.

    Uma combinação cujo modo ainda não foi implementado fica de fora e é listada
    em ``comparacao_pendentes``; qualquer outro erro cancela a comparação.
    """
    st.session_state["erro"] = None
    base: ResultadoExecucao = st.session_state["resultado"]
    cfg = base.config
    resultados: list[ResultadoExecucao] = []
    pendentes: list[str] = []
    for modo in MODOS:
        for variante in VARIANTES:
            config = ConfiguracaoExecucao(
                n=cfg.n,
                inicio=cfg.inicio,
                modo=modo,
                variante=variante,
                seed=base.seed_utilizada,
                max_estados=(cfg.max_estados or int(st.session_state["cfg_orcamento"]))
                if modo == "recuo" else None,
            )
            try:
                resultados.append(core.api.resolver(config))
            except NotImplementedError:
                pendentes.append(rotulo_combinacao(modo, variante))
            except (ValueError, RuntimeError) as erro:
                st.session_state["erro"] = mensagem_de_erro(config, erro)
                return
    if not resultados:
        st.session_state["erro"] = "Nenhuma das combinações está disponível nesta versão do código."
        return
    st.session_state["comparacao"] = resultados
    st.session_state["comparacao_pendentes"] = pendentes


# --------------------------------------------------------------------------- partes comuns


def _menu_lateral() -> None:
    st.sidebar.markdown(
        '<div class="menu-marca"><div class="marca" aria-hidden="true">♞</div>'
        "<span>Passeio do Cavalo</span></div>",
        unsafe_allow_html=True,
    )
    atual = st.session_state["tela"]
    destaque = "resultados" if atual == "percurso" else atual
    for tela, rotulo in TELAS.items():
        if tela == "resultados" and st.session_state["resultado"] is None:
            continue
        st.sidebar.button(
            rotulo,
            key=f"menu_{tela}",
            type="primary" if tela == destaque else "secondary",
            on_click=_ir,
            args=(tela,),
            width="stretch",
        )
    st.sidebar.markdown(
        '<div class="menu-rodape">NCC0234 Complexidade de Algoritmos<br>UERN, 2026.2</div>',
        unsafe_allow_html=True,
    )


def _barra_topo(mostrar_marca: bool = True) -> None:
    """Marca do sistema no topo das telas internas."""
    if mostrar_marca:
        st.markdown(
            '<div class="topo"><div class="marca" aria-hidden="true">♞</div>'
            '<div class="nome">Passeio do Cavalo<span>Estratégia PARE e Análise de Complexidade'
            "</span></div></div>",
            unsafe_allow_html=True,
        )


def _titulo(texto: str, apoio: str | None = None) -> None:
    html = f'<div class="titulo-tela" role="heading" aria-level="1">{escape(texto)}</div>'
    if apoio:
        html += f'<p class="apoio-tela">{apoio}</p>'
    st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- telas


def _tela_inicio() -> None:
    _barra_topo(mostrar_marca=False)
    _, centro, _ = st.columns([1, 3, 1])
    with centro:
        parte1, parte2 = TITULO.split(" — ", 1)
        st.markdown(
            f"""
<div class="capa">
  <div class="marca" aria-hidden="true">♞</div>
  <h1>{parte1}</h1>
  <p class="subtitulo">{parte2}</p>
  <p class="resumo">Um cavalo de xadrez precisa visitar todas as casas do tabuleiro, sem repetir
  nenhuma. Este sistema constrói esses percursos com a estratégia PARE e mede quanto da
  tarefa ela cumpre e quanto esforço computacional isso custa, em tabuleiros 5×5 e 8×8.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        b1.button("Iniciar análise", type="primary", on_click=_ir, args=("configurar",),
                  width="stretch")
        b2.button("Sobre o sistema", on_click=_ir, args=("sobre",), width="stretch")
        st.markdown(
            '<p class="capa rodape" style="padding:0">Trabalho Final T3 de NCC0234 Complexidade '
            "de Algoritmos<br>Universidade do Estado do Rio Grande do Norte, 2026.2, "
            "Profa. Rosiery Maia</p>",
            unsafe_allow_html=True,
        )


def _tela_sobre() -> None:
    _barra_topo()
    _titulo("Sobre o sistema",
            "O que o sistema faz, como a estratégia PARE decide e o que cada métrica mede.")
    st.markdown(
        """
#### O problema

O cavalo do xadrez anda em "L". O desafio é escolher uma casa inicial e fazer o cavalo
passar por todas as casas do tabuleiro **exatamente uma vez**, sem precisar voltar ao início.
Nem sempre a estratégia consegue: nesses casos o sistema devolve o maior percurso que
encontrou e explica por que parou.

#### Como o PARE escolhe o próximo salto

Para cada salto possível até uma casa `v`, o algoritmo simula a entrada em `v` e olha o
**grafo residual**: `v` mais as casas ainda livres, ligadas pelos saltos do cavalo. Os
candidatos são ordenados pelos critérios abaixo, um de cada vez, sem pesos.

| Critério | O que conta | Preferência |
|---|---|---|
| **F**, fragmentação | pedaços desconectados do grafo residual | menos |
| **I**, isolamento | casas livres sem nenhum vizinho livre | menos |
| **P**, pressão de extremidades | casas livres com um único vizinho livre | menos |
| **A**, acessibilidade | saltos livres a partir de `v` | restritiva: menos; expansiva: mais |

A variante restritiva usa no último critério a regra de Warnsdorff (1823). A expansiva
testa a hipótese oposta. O **modo guloso** segue sempre o primeiro da ordem e não volta
atrás. O **modo com recuo** volta à última escolha com alternativas quando fica sem saída,
até completar o passeio ou gastar o orçamento `max_estados`.

#### O que é medido

- **Estados**: entradas em caminhos parciais válidos.
- **Verificações**: entradas lidas de listas de adjacência durante a resolução.
- **Avaliações**: cálculos da chave `(F, I, P, A)`.
- **Recuos**: casas removidas do caminho ao voltar atrás.
- **Tempo**: só a resolução, sem contar o desenho na tela.

#### Sobre a animação

O algoritmo roda primeiro e, só depois, a tela reproduz o melhor percurso que ele
encontrou. A animação não mostra as tentativas descartadas pela busca.
        """
    )
    st.button("Iniciar análise", type="primary", on_click=_ir, args=("configurar",))


def _tela_configurar() -> None:
    _barra_topo()
    _titulo("Nova análise",
            "Escolha o tabuleiro, a casa inicial e a forma de busca. O tabuleiro ao lado "
            "mostra de onde o cavalo vai partir.")
    if st.session_state["erro"]:
        st.error(st.session_state["erro"])

    formulario, previa = st.columns([2, 3], gap="large")
    with formulario, st.container(border=True):
        n = st.radio("Tabuleiro", DIMENSOES_OBRIGATORIAS, format_func=lambda v: f"{v}×{v}",
                     horizontal=True, key="cfg_n")
        for chave in ("cfg_linha", "cfg_coluna"):
            st.session_state[chave] = min(int(st.session_state[chave]), n)
        c1, c2 = st.columns(2)
        c1.number_input("Linha inicial", 1, n, key="cfg_linha")
        c2.number_input("Coluna inicial", 1, n, key="cfg_coluna")
        st.radio("Modo", MODOS, format_func=ROTULO_MODO.get, key="cfg_modo")
        st.radio("Variante", VARIANTES, format_func=ROTULO_VARIANTE.get, key="cfg_variante")
        st.number_input("Orçamento (max_estados)", min_value=1, step=1000, key="cfg_orcamento",
                        disabled=st.session_state["cfg_modo"] != "recuo",
                        help="Limite de estados explorados no modo com recuo.")
        st.checkbox("Usar semente fixa", key="cfg_seed_fixa",
                    help="Sem semente fixa, uma é gerada e exibida no resultado.")
        st.number_input("Semente", step=1, key="cfg_seed",
                        disabled=not st.session_state["cfg_seed_fixa"])
        st.button("Executar análise", type="primary", on_click=_executar,
                  width="stretch")

    with previa:
        args = argumentos_formulario()
        linha0 = args["linha"] - 1
        desenhar_tabuleiro(
            argumentos_tabuleiro("previa", n, (linha0, args["coluna"] - 1),
                                 cor=cor_pela_posicao(n, linha0)),
            chave="tabuleiro_previa",
        )


def _tela_percurso() -> None:
    resultado: ResultadoExecucao = st.session_state["resultado"]
    cfg = resultado.config
    _barra_topo()
    _titulo("Percurso do cavalo",
            f"Tabuleiro {cfg.n}×{cfg.n}, início {formatar_casa(cfg.inicio)}, "
            f"{ROTULO_MODO[cfg.modo].lower()}, variante {cfg.variante}.")
    st.button("Pular para os resultados ⏭", on_click=_ir, args=("resultados",))

    execucao = st.session_state["execucao"]
    retorno = desenhar_tabuleiro(
        argumentos_tabuleiro("animacao", cfg.n, cfg.inicio, resultado.melhor_percurso,
                             cor=cor_pela_posicao(cfg.n, cfg.inicio[0]), execucao=execucao),
        chave=f"tabuleiro_animacao_{execucao}",
    )
    if retorno and retorno.get("evento") == "fim" and retorno.get("execucao") == execucao:
        st.session_state["tela"] = "resultados"
        st.rerun()


def _tela_resultados() -> None:
    resultado: ResultadoExecucao | None = st.session_state["resultado"]
    _barra_topo()
    if resultado is None:
        _titulo("Resultados", "Nenhuma análise foi executada ainda.")
        st.button("Iniciar análise", type="primary", on_click=_ir, args=("configurar",))
        return
    if st.session_state["erro"]:
        st.error(st.session_state["erro"])

    cfg = resultado.config
    st.markdown(
        f'<div class="conclusao" role="heading" aria-level="1">{frase_conclusao(resultado)}</div>'
        f'<p class="apoio-tela">Maior percurso encontrado dentro do orçamento e das regras de '
        f"busca. Tabuleiro {cfg.n}×{cfg.n}, início {formatar_casa(cfg.inicio)}, "
        f"{ROTULO_MODO[cfg.modo].lower()}, variante {cfg.variante}.</p>",
        unsafe_allow_html=True,
    )
    with st.container(horizontal=True):
        st.button("Novo teste", type="primary", on_click=_ir, args=("configurar",))
        st.button("Rever animação", on_click=_rever_animacao)
        st.button("Comparar as 4 combinações", on_click=_comparar)

    col_tab, col_ind = st.columns([2, 1], gap="large")
    with col_tab:
        desenhar_tabuleiro(
            argumentos_tabuleiro("analise", cfg.n, cfg.inicio, resultado.melhor_percurso,
                                 cor=cor_pela_posicao(cfg.n, cfg.inicio[0]),
                                 execucao=st.session_state["execucao"]),
            chave="tabuleiro_analise",
        )
        st.caption("Clique num lance da súmula, use as setas do teclado ou o botão Reproduzir.")
    with col_ind:
        st.markdown(gerar_html_eficacia(resultado, conferir_percurso(resultado)),
                    unsafe_allow_html=True)
    st.markdown(gerar_html_eficiencia(resultado), unsafe_allow_html=True)

    comparacao: list[ResultadoExecucao] | None = st.session_state["comparacao"]
    if comparacao:
        _secao_comparacao(comparacao)


def _secao_comparacao(resultados: list[ResultadoExecucao]) -> None:
    cfg = resultados[0].config
    titulo = ("Comparação das 4 combinações" if len(resultados) == 4
              else f"Comparação de {len(resultados)} combinações")
    _titulo(titulo,
            f"Mesma casa inicial {formatar_casa(cfg.inicio)} e mesma semente. Exploração ao vivo: "
            "os números do relatório vêm de <code>results/experiments.csv</code>.")
    pendentes = st.session_state.get("comparacao_pendentes") or []
    if pendentes:
        st.info("Ainda não disponíveis nesta versão do código: " + ", ".join(pendentes) + ".")
    st.markdown(gerar_html_cartoes_comparacao(resultados), unsafe_allow_html=True)
    df = pd.DataFrame([resultado_para_linha(r) for r in resultados])
    st.pyplot(grafico_comparativo(df), width="stretch")
    st.dataframe(
        df.drop(columns=["modo", "variante"]),
        width="stretch",
        hide_index=True,
        column_config={
            "combinacao": "Combinação",
            "casas_visitadas": "Casas",
            "cobertura_percentual": st.column_config.NumberColumn("Cobertura %", format="%.2f"),
            "passeio_completo": "Completo?",
            "motivo_parada": "Motivo",
            "tempo_segundos": st.column_config.NumberColumn("Tempo (s)", format="%.6f"),
            "estados_explorados": "Estados",
            "verificacoes_movimentos": "Verificações",
            "avaliacoes_candidatos": "Avaliações",
            "recuos": "Recuos",
        },
    )


def _tela_experimentos() -> None:
    _barra_topo()
    _titulo("Experimentos",
            "Protocolo obrigatório: quatro cenários (5×5 e 8×8, duas casas iniciais cada), "
            "dois modos e duas variantes, com a mesma semente.")
    st.caption("Tabela lida de `results/experiments.csv`, gerado por "
               "`experiments/run_experiments.py`. A interface não gera números próprios.")
    df = carregar_experimentos()
    if df is None:
        st.info("O arquivo `results/experiments.csv` ainda não existe. Gere com "
                "`python experiments/run_experiments.py --saida results/experiments.csv`.")
        return

    st.markdown(gerar_html_resumo_experimentos(df), unsafe_allow_html=True)
    df = rotular_cenarios(df)
    colunas_graficos = {"cenario", "modo", "variante"} | {c for c, _, _ in METRICAS_GRAFICO}
    if colunas_graficos <= set(df.columns):
        st.pyplot(grafico_comparativo(df, grupo="rotulo_cenario"), width="stretch")
    else:
        faltando = sorted(colunas_graficos - set(df.columns))
        st.caption(f"Gráficos indisponíveis: faltam as colunas {', '.join(faltando)}.")

    principais = [c for c in COLUNAS_TABELA_EXPERIMENTOS if c in df.columns]
    st.dataframe(df[principais] if principais else df.drop(columns="rotulo_cenario"),
                 width="stretch", hide_index=True, column_config=CONFIG_COLUNAS_EXPERIMENTOS)
    with st.expander("Todas as colunas do CSV"):
        st.dataframe(df.drop(columns="rotulo_cenario"), width="stretch", hide_index=True)
    st.download_button("Baixar CSV", df.drop(columns="rotulo_cenario").to_csv(index=False)
                       .encode("utf-8"), file_name="experiments.csv", mime="text/csv")


TELAS_FUNCOES = {
    "inicio": _tela_inicio,
    "sobre": _tela_sobre,
    "configurar": _tela_configurar,
    "percurso": _tela_percurso,
    "resultados": _tela_resultados,
    "experimentos": _tela_experimentos,
}


def main() -> None:
    """Monta a página Streamlit e despacha para a tela atual."""
    st.set_page_config(page_title="Passeio do Cavalo — PARE", page_icon="♞", layout="wide",
                       initial_sidebar_state="collapsed")
    _inicializar_estado()
    if st.session_state["tela"] in ("percurso", "resultados") and st.session_state["resultado"] is None:
        st.session_state["tela"] = "configurar"
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)
    _menu_lateral()
    TELAS_FUNCOES[st.session_state["tela"]]()


if __name__ == "__main__":
    main()
