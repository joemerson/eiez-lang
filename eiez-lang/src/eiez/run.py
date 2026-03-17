#!/usr/bin/env python3
# eiez-lang/run.py
"""
EIEZ — Compilar + Simular em um comando.

Uso:
    python run.py examples\01_bell_state.eiez
    python run.py examples\01_bell_state.eiez --shots 5
    python run.py examples\02_optimize_gate.eiez --backend zie
    python run.py examples\03_for_loop_4qubits.eiez
    python run.py examples\04_teleportation.eiez
"""

import sys
import os
import argparse


# ---------------------------------------------------------------------------
# Localiza src/eiez automaticamente — funciona em qualquer estrutura de pasta
# ---------------------------------------------------------------------------
def _find_src():
    base = os.path.dirname(os.path.abspath(__file__))
    # Tenta no próprio diretório e até 3 níveis acima
    check = base
    for _ in range(4):
        candidate = os.path.join(check, "src")
        if os.path.isdir(os.path.join(candidate, "eiez")):
            return candidate
        check = os.path.dirname(check)
    # Tenta em subpastas diretas (caso haja pasta extra de download)
    try:
        for entry in os.listdir(base):
            candidate = os.path.join(base, entry, "src")
            if os.path.isdir(os.path.join(candidate, "eiez")):
                return candidate
    except Exception:
        pass
    return None


_src = _find_src()
if _src is None:
    here = os.path.dirname(os.path.abspath(__file__))
    print("=" * 56)
    print("ERRO: Nao encontrei a pasta src\\eiez\\")
    print(f"  Rodando de: {here}")
    print("")
    print("  Estrutura esperada:")
    print("    run.py")
    print("    src\\eiez\\__init__.py")
    print("    examples\\01_bell_state.eiez")
    print("")
    print("  O que existe aqui agora:")
    for item in sorted(os.listdir(here)):
        print(f"    {item}")
    print("=" * 56)
    sys.exit(1)

sys.path.insert(0, _src)

# ---------------------------------------------------------------------------
# Imports do compilador
# ---------------------------------------------------------------------------
from eiez.parser import parse
from eiez.generator_qasm import generate_qasm
from eiez.optimizer_interface import create_optimizer
from eiez.simulator import SimRunner


def main():
    cli = argparse.ArgumentParser(
        prog="eiez",
        description="EIEZ Compiler + Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run.py examples\\01_bell_state.eiez
  python run.py examples\\01_bell_state.eiez --shots 5
  python run.py examples\\02_optimize_gate.eiez --backend zie
  python run.py examples\\04_teleportation.eiez
        """
    )
    cli.add_argument("input",     help="arquivo .eiez")
    cli.add_argument("-o",        "--output",  default=None,  help="salvar .qasm (opcional)")
    cli.add_argument("--backend", choices=["auto", "null", "zie"], default="auto")
    cli.add_argument("--shots",   type=int, default=1, help="numero de execucoes (padrao: 1)")
    cli.add_argument("--qasm-only", action="store_true", help="so mostra o QASM, sem simular")
    args = cli.parse_args()

    # 1. Ler fonte
    try:
        with open(args.input, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo nao encontrado: {args.input}")
        sys.exit(1)

    print(f"\n> Compilando: {args.input}  [backend={args.backend}]")

    # 2. Compilar
    try:
        program   = parse(source)
        optimizer = create_optimizer(args.backend)
        params    = optimizer.apply_all(program)
        qasm      = generate_qasm(program, optimizer)
    except SyntaxError as e:
        print(f"ERRO de sintaxe:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERRO: {e}")
        sys.exit(1)

    print("OK Compilado com sucesso!")

    # 3. Mostrar QASM
    print("\n-- QASM gerado " + "-" * 40)
    print(qasm)
    print("-" * 56)

    # 4. Salvar QASM se pedido
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(qasm)
        print(f"Salvo em: {args.output}")

    if args.qasm_only:
        return

    # 5. Simular
    for shot in range(args.shots):
        if args.shots > 1:
            print(f"\n{'='*20} Shot {shot + 1}/{args.shots} {'='*20}")
        runner = SimRunner(program, params)
        runner.run()


if __name__ == "__main__":
    main()
