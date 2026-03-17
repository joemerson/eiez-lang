#!/usr/bin/env python3
# eiez-lang/run.py
"""
EIEZ — Compilar + Simular em um comando.

Uso:
    python run.py examples/01_bell_state.eiez
    python run.py examples/02_optimize_gate.eiez --backend zie
    python run.py examples/03_for_loop_4qubits.eiez
    python run.py examples/04_teleportation.eiez
    python run.py examples/01_bell_state.eiez --shots 5
"""

import sys
import os
import argparse

# Adiciona src/ ao path para importar sem instalar
_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, "src"))
sys.path.insert(0, os.path.join(_base, "..", "src"))  # caso rode de subpasta

from eiez.parser import parse
from eiez.generator_qasm import generate_qasm
from eiez.optimizer_interface import create_optimizer
from eiez.simulator import SimRunner


def main():
    cli = argparse.ArgumentParser(
        description="EIEZ Compiler + Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run.py examples/01_bell_state.eiez
  python run.py examples/02_optimize_gate.eiez --backend zie
  python run.py examples/04_teleportation.eiez --shots 3
        """
    )
    cli.add_argument("input",   help="arquivo .eiez")
    cli.add_argument("-o",      "--output",  default=None,  help="salvar .qasm (opcional)")
    cli.add_argument("--backend", choices=["auto","null","zie"], default="auto")
    cli.add_argument("--shots", type=int, default=1, help="número de execuções (padrão: 1)")
    cli.add_argument("--qasm-only", action="store_true", help="só mostra o QASM gerado, sem simular")
    args = cli.parse_args()

    # 1. Ler fonte
    try:
        with open(args.input, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {args.input}")
        sys.exit(1)

    print(f"\n▸ Compilando: {args.input}  [backend={args.backend}]")

    # 2. Compilar
    try:
        program   = parse(source)
        optimizer = create_optimizer(args.backend)
        params    = optimizer.apply_all(program)
        qasm      = generate_qasm(program, optimizer)
    except SyntaxError as e:
        print(f"❌ Erro de sintaxe:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

    print(f"✅ Compilado com sucesso!")

    # 3. Mostrar QASM
    print("\n── QASM gerado ─────────────────────────────────")
    print(qasm)
    print("────────────────────────────────────────────────")

    # 4. Salvar QASM se pedido
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(qasm)
        print(f"💾 QASM salvo em: {args.output}")

    if args.qasm_only:
        return

    # 5. Simular
    for shot in range(args.shots):
        if args.shots > 1:
            print(f"\n{'─'*20} Shot {shot + 1}/{args.shots} {'─'*20}")
        runner = SimRunner(program, params)
        runner.run()


if __name__ == "__main__":
    main()
