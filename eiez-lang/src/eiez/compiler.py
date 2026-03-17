# src/eiez/compiler.py
"""
EIEZ Compiler — ponto de entrada da CLI.

Orquestra o pipeline sem reimplementar nenhuma etapa:

  .eiez source
      └─ lexer.py       → tokens
      └─ parser.py      → ProgramIR
      └─ optimizer_interface.py → resolve optimize stmts (via backend escolhido)
      └─ generator_qasm.py     → OpenQASM 2.0 string
      └─ qasm_linter.py        → validação e métricas (opcional)

O compilador não importa zie_core, _zie_engine, nem qualquer motor interno.
A escolha do backend é feita uma única vez, aqui, via --backend flag.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import parse
from .generator_qasm import generate_qasm
from .optimizer_interface import create_optimizer


# ---------------------------------------------------------------------------
# API programática
# ---------------------------------------------------------------------------

def compile_source(
    source: str,
    backend: str = "auto",
) -> str:
    """
    Compila código-fonte EIEZ e retorna string OpenQASM 2.0.

    backend:
        "auto"  — usa motor interno se disponível, senão NullBackend
        "null"  — nunca usa motor externo (útil para testes e distribuição)
        "zie"   — exige motor interno (lança RuntimeError se ausente)
    """
    program  = parse(source)
    optimizer = create_optimizer(backend)
    return generate_qasm(program, optimizer)


def compile_file(
    input_path: str,
    output_path: str,
    backend: str = "auto",
) -> None:
    """Lê um arquivo .eiez, compila e grava o .qasm resultante."""
    src_path = Path(input_path)

    try:
        source = src_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {input_path}")
        sys.exit(1)
    except UnicodeDecodeError:
        source = src_path.read_text(encoding="latin-1")

    try:
        qasm = compile_source(source, backend=backend)
    except SyntaxError as e:
        print(f"❌ Erro de sintaxe: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro de compilação: {e}")
        sys.exit(1)

    Path(output_path).write_text(qasm, encoding="utf-8")
    print(f"✅ {input_path}  →  {output_path}  [backend={backend}]")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    cli = argparse.ArgumentParser(
        prog="eiez",
        description="EIEZ Compiler — compila .eiez para OpenQASM 2.0",
    )
    cli.add_argument("input",  help="arquivo .eiez de entrada")
    cli.add_argument("-o", "--output", default="out.qasm", help="arquivo .qasm de saída")
    cli.add_argument(
        "--backend",
        choices=["auto", "null", "zie"],
        default="auto",
        help=(
            "motor de otimização: "
            "'auto' usa motor interno se disponível (padrão), "
            "'null' desativa otimização, "
            "'zie' exige motor interno"
        ),
    )
    cli.add_argument("--lint", action="store_true", help="executa linter após compilar")

    args = cli.parse_args()
    compile_file(args.input, args.output, backend=args.backend)

    if args.lint:
        from .qasm_linter import lint_qasm
        lint_qasm(args.output)


if __name__ == "__main__":
    main()
