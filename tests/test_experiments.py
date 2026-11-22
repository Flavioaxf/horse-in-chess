from __future__ import annotations

import ast
import csv
from pathlib import Path

import pytest

import experiments.run_experiments as run_experiments_module
from core.tipos import ResultadoValidacao
from experiments.cenarios import (
    CENARIOS_OBRIGATORIOS,
    CenarioExperimental,
    gerar_configuracoes_protocolo,
)
from experiments.run_experiments import COLUNAS_CSV, executar_protocolo, main

RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def test_cenarios_obrigatorios_correspondem_ao_protocolo() -> None:
    resumo = [
        (c.codigo, c.n, c.linha_1based, c.coluna_1based)
        for c in CENARIOS_OBRIGATORIOS
    ]
    assert resumo == [
        ("T01", 5, 1, 1),
        ("T02", 5, 1, 2),
        ("T03", 8, 1, 1),
        ("T04", 8, 4, 4),
    ]


def test_gerar_configuracoes_protocolo_16_combinacoes_e_conversao_0based() -> None:
    pares = gerar_configuracoes_protocolo(seed=2026, max_estados=10_000)

    assert len(pares) == 16

    combinacoes_vistas: set[tuple[str, str, str]] = set()
    inicio_por_cenario: dict[str, tuple[int, int]] = {}

    for cenario, config in pares:
        chave = (cenario.codigo, config.modo, config.variante)
        assert chave not in combinacoes_vistas
        combinacoes_vistas.add(chave)

        assert config.n == cenario.n
        assert config.inicio == (cenario.linha_1based - 1, cenario.coluna_1based - 1)
        assert config.seed == 2026
        assert config.podar_inviaveis is False
        if config.modo == "recuo":
            assert config.max_estados == 10_000
        else:
            assert config.max_estados is None

        inicio_por_cenario[cenario.codigo] = config.inicio

    assert inicio_por_cenario == {
        "T01": (0, 0),
        "T02": (0, 1),
        "T03": (0, 0),
        "T04": (3, 3),
    }


@pytest.mark.parametrize("seed_invalida", [True, False, "2026", 1.5, None])
def test_gerar_configuracoes_rejeita_seed_invalida(seed_invalida: object) -> None:
    with pytest.raises(ValueError, match="Semente inválida"):
        gerar_configuracoes_protocolo(seed=seed_invalida)  # type: ignore[arg-type]


@pytest.mark.parametrize("max_invalido", [0, -10, True, "100"])
def test_gerar_configuracoes_rejeita_max_estados_invalido(max_invalido: object) -> None:
    with pytest.raises(ValueError, match="max_estados inválido"):
        gerar_configuracoes_protocolo(max_estados=max_invalido)  # type: ignore[arg-type]


def test_gerar_configuracoes_rejeita_cenario_fora_dos_limites() -> None:
    cenario_invalido = CenarioExperimental("TX", 5, 0, 1, "Fora do limite 1-based")
    with pytest.raises(ValueError, match="fora do tabuleiro"):
        gerar_configuracoes_protocolo(cenarios=(cenario_invalido,))


def test_executar_protocolo_exporta_16_linhas_validadas_e_colunas_completas(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "subpasta" / "experiments.csv"

    caminho_retornado = executar_protocolo(
        caminho_saida=destino,
        seed=2026,
        max_estados=40,
    )

    assert caminho_retornado == destino
    assert destino.is_file()

    with destino.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        assert tuple(leitor.fieldnames or ()) == COLUNAS_CSV
        linhas = list(leitor)

    assert len(linhas) == 16

    colunas_interface = {
        "cenario",
        "modo",
        "variante",
        "cobertura_percentual",
        "estados_explorados",
        "verificacoes_movimentos",
        "tempo_segundos",
    }
    assert colunas_interface <= set(COLUNAS_CSV)

    for linha in linhas:
        assert linha["validador_aprovado"] == "True"
        assert linha["seed"] == "2026"
        assert linha["versao_codigo"] != ""
        assert linha["python_versao"] != ""
        assert linha["sistema_operacional"] != ""
        assert linha["processador"] != ""

        casas = int(linha["casas_visitadas"])
        total = int(linha["total_casas"])
        estados = int(linha["estados_explorados"])
        recuos = int(linha["recuos"])
        cobertura = float(linha["cobertura_percentual"])
        tempo = float(linha["tempo_segundos"])

        assert 1 <= casas <= total
        assert cobertura == pytest.approx((100.0 * casas) / total, abs=0.01)
        assert tempo >= 0.0

        if linha["cenario"] == "T02":
            assert linha["impossibilidade_paridade"] == "True"
            assert linha["passeio_completo"] == "False"
            assert casas <= 24
        else:
            assert linha["impossibilidade_paridade"] == "False"

        if linha["modo"] == "guloso":
            assert linha["max_estados"] == ""
            assert recuos == 0
            assert linha["motivo_parada"] in {"completo", "sem_movimentos"}
        else:
            assert linha["max_estados"] == "40"
            assert estados <= 40
            assert linha["motivo_parada"] in {
                "completo",
                "busca_esgotada",
                "limite_estados",
            }


def test_executar_protocolo_aborta_e_nao_grava_se_validador_rejeitar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def validador_falso(*args: object, **kwargs: object) -> ResultadoValidacao:
        return ResultadoValidacao(
            valido=False,
            passeio_completo=False,
            erros=("Salto inválido simulado",),
        )

    monkeypatch.setattr(run_experiments_module, "validar_percurso", validador_falso)
    destino = tmp_path / "falha.csv"

    with pytest.raises(RuntimeError, match="Validador independente rejeitou"):
        executar_protocolo(caminho_saida=destino, seed=2026, max_estados=10)

    assert not destino.exists()


def test_main_executa_via_cli_e_trata_parametro_invalido(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "cli_experiments.csv"

    codigo_ok = main(
        ["--saida", str(destino), "--seed", "2026", "--max-estados", "30"]
    )
    saida_ok = capsys.readouterr().out

    assert codigo_ok == 0
    assert destino.is_file()
    assert "16 execuções validadas" in saida_ok
    assert "T01" in saida_ok and "T04" in saida_ok

    codigo_erro = main(["--saida", str(tmp_path / "err.csv"), "--max-estados", "0"])
    erro_stderr = capsys.readouterr().err
    assert codigo_erro == 2
    assert "Erro de parâmetro" in erro_stderr


def test_experiments_respeita_fronteira_arquitetural() -> None:
    proibidos = {"core.pare", "core.busca"}
    for arquivo in (RAIZ_PROJETO / "experiments").glob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        imports: set[str] = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for alias in no.names:
                    imports.add(alias.name)
            elif isinstance(no, ast.ImportFrom) and no.module:
                imports.add(no.module)
        assert imports.isdisjoint(proibidos), (
            f"{arquivo.name} violou a fronteira arquitetural importando {imports & proibidos}"
        )
