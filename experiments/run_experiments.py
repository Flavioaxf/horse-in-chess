from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from core.api import resolver  # noqa: F401
from core.validator import validar_percurso  # noqa: F401
from experiments.cenarios import gerar_configuracoes_protocolo  # noqa: F401


def executar_protocolo(
    caminho_saida: Path,
    seed: int = 2026,
    max_estados: int = 10_000,
) -> Path:
    raise NotImplementedError("Implementar executar_protocolo na feature F9 (experimentos).")


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("Implementar main na feature F9 (experimentos).")


if __name__ == "__main__":
    raise SystemExit(main())
