from __future__ import annotations

import argparse
from collections.abc import Sequence

from core.api import resolver  # noqa: F401
from core.render import (  # noqa: F401
    formatar_resumo_execucao,
    formatar_tabuleiro_texto,
)
from core.tipos import ConfiguracaoExecucao  # noqa: F401


def construir_parser() -> argparse.ArgumentParser:
    raise NotImplementedError("Implementar construir_parser na feature F4 (render-cli).")


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("Implementar main na feature F4 (render-cli).")


if __name__ == "__main__":
    raise SystemExit(main())
