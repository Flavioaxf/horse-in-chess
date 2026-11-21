"""Testes do contrato de dados (core/tipos.py) e das fronteiras arquiteturais.

Garante na F0 que o contrato compartilhado e as regras de dependência 
estejam consistentes antes do trabalho em paralelo.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core import (
    AvaliacaoCandidato,
    ConfiguracaoExecucao,
    DIMENSOES_OBRIGATORIAS,
    MODOS_VALIDOS,
    MOTIVOS_PARADA_VALIDOS,
    ResultadoExecucao,
    ResultadoValidacao,
    VARIANTES_VALIDAS,
    resolver,
)
from core.board import KNIGHT_MOVES

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DIR_CORE = RAIZ_PROJETO / "core"


def _coletar_imports(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    modulos: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                modulos.add(alias.name)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


def test_configuracao_valores_padrao_e_imutabilidade() -> None:
    cfg = ConfiguracaoExecucao(n=8, inicio=(0, 0), modo="guloso")

    assert cfg.n == 8
    assert cfg.inicio == (0, 0)
    assert cfg.modo == "guloso"
    assert cfg.variante == "restritiva"
    assert cfg.seed is None
    assert cfg.max_estados is None
    assert cfg.podar_inviaveis is False

    with pytest.raises(FrozenInstanceError):
        cfg.n = 5  # type: ignore[misc]


def test_constantes_valores_fechados() -> None:
    assert DIMENSOES_OBRIGATORIAS == (5, 8)
    assert MODOS_VALIDOS == {"guloso", "recuo"}
    assert VARIANTES_VALIDAS == {"restritiva", "expansiva"}
    assert MOTIVOS_PARADA_VALIDOS == {
        "completo",
        "sem_movimentos",
        "busca_esgotada",
        "limite_estados",
    }
    assert len(KNIGHT_MOVES) == 8
    assert len(set(KNIGHT_MOVES)) == 8


def test_dataclasses_avaliacao_validacao_e_resultado() -> None:
    avaliacao = AvaliacaoCandidato(
        candidato=(2, 1),
        fragmentacao=1,
        isolamento=0,
        pressao=1,
        acessibilidade=5,
        completo_ainda_possivel=True,
    )
    assert avaliacao.completo_ainda_possivel is True

    validacao = ResultadoValidacao(valido=True, passeio_completo=False)
    assert validacao.erros == ()

    cfg = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 0),
        modo="recuo",
        variante="restritiva",
        seed=2026,
        max_estados=10_000,
    )
    resultado = ResultadoExecucao(
        config=cfg,
        seed_utilizada=2026,
        melhor_percurso=[(0, 0)],
        casas_visitadas=1,
        total_casas=25,
        cobertura_percentual=4.0,
        passeio_completo=False,
        motivo_parada="limite_estados",
        tempo_segundos=0.0,
        estados_explorados=1,
        verificacoes_movimentos=0,
        verificacoes_preparo=200,
        avaliacoes_candidatos=0,
        recuos=0,
        impossibilidade_paridade=False,
        versao_codigo="dev",
    )
    assert resultado.estados_sem_completo_possivel == 0


def test_core_nao_importa_dependencias_proibidas_nem_usa_print() -> None:
    proibidos = {"streamlit", "pandas", "matplotlib", "experiments"}

    for arquivo in DIR_CORE.glob("*.py"):
        imports = _coletar_imports(arquivo)
        raizes = {imp.split(".")[0] for imp in imports}
        assert raizes.isdisjoint(proibidos), (
            f"{arquivo.name} importou módulos proibidos: {raizes & proibidos}"
        )

        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for no in ast.walk(arvore):
            if (
                isinstance(no, ast.Call)
                and isinstance(no.func, ast.Name)
                and no.func.id == "print"
            ):
                pytest.fail(f"Uso proibido de print() encontrado em core/{arquivo.name}.")


def test_limites_estritos_de_validator_e_render() -> None:
    imports_validator = _coletar_imports(DIR_CORE / "validator.py")
    internos_validator = {imp for imp in imports_validator if imp.startswith("core")}
    assert internos_validator <= {"core.board", "core.tipos"}

    imports_render = _coletar_imports(DIR_CORE / "render.py")
    internos_render = {imp for imp in imports_render if imp.startswith("core")}
    assert internos_render <= {"core.tipos"}


def test_assinatura_publica_resolver() -> None:
    assert callable(resolver)
    parametros = list(inspect.signature(resolver).parameters)
    assert parametros == ["config"]
