# src/qasm_linter.py - Linter/Validador Básico de Código OpenQASM 

import re
import sys
import argparse

def lint_qasm(file_path: str):
    """
    Analisa um arquivo QASM, verifica a sintaxe e calcula métricas de complexidade.
    """
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo não encontrado: {file_path}")
        return

    print(f"--- Analisando o arquivo: {file_path} ---")
    
    # 1. Variáveis de Análise
    errors = 0
    warnings = 0
    metrics = {
        'qreg_size': 0,
        'creg_size': 0,
        'gates_1q': 0,  # h, x, y, z, rx, ry, rz
        'gates_2q': 0,  # cx, cz
        'measures': 0,
        'instructions': 0
    }
    
    # Padrões Regex para portas e declarações
    REGEX_QREG = re.compile(r'qreg\s+([a-zA-Z0-9_]+)\[(\d+)\];')
    REGEX_CREG = re.compile(r'creg\s+([a-zA-Z0-9_]+)\[(\d+)\];')
    REGEX_GATE_1Q = re.compile(r'(h|x|y|z|rx|ry|rz)\s*(\([^\)]*\))?\s+([a-zA-Z0-9_]+)\[(\d+)\];')
    REGEX_GATE_2Q = re.compile(r'(cx|cz)\s+([a-zA-Z0-9_]+)\[(\d+)\],\s*([a-zA-Z0-9_]+)\[(\d+)\];')
    REGEX_MEASURE = re.compile(r'measure\s+([a-zA-Z0-9_]+)\[(\d+)\]\s*->\s*([a-zA-Z0-9_]+)\[(\d+)\];')
    
    # Estado para pular o corpo das definições de gate
    in_gate_definition = False

    # 2. Análise Linha por Linha
    for i, line in enumerate(lines):
        line_num = i + 1
        clean_line = line.strip()
        
        # Ignorar linhas de comentário e linhas vazias
        if not clean_line or clean_line.startswith('//'):
            continue
        
        # --- Lógica para lidar com definições de Gate (Custom Gate) ---
        if clean_line.startswith('gate'):
            in_gate_definition = True
            continue
        
        if in_gate_definition:
            if clean_line.endswith('}'):
                in_gate_definition = False
            continue
        # -----------------------------------------------------------------

        metrics['instructions'] += 1

        # A. Validação de Cabeçalho (Verifica as duas primeiras linhas não-comentário)
        if line_num == 1:
             # A primeira instrução real deve ser OPENQASM ou uma declaração
             if not clean_line.startswith('OPENQASM'):
                 print(f"🚫 ERRO (L{line_num}): O arquivo QASM deve começar com 'OPENQASM 2.0;' após comentários. -> {clean_line[:30]}...")
                 errors += 1
        
        # B. Contagem e Registro de Declarações
        if match := REGEX_QREG.match(clean_line):
            metrics['qreg_size'] = int(match.group(2))
        elif match := REGEX_CREG.match(clean_line):
            metrics['creg_size'] = int(match.group(2))

        # C. Contagem de Portas
        elif REGEX_GATE_1Q.match(clean_line):
            metrics['gates_1q'] += 1
        elif REGEX_GATE_2Q.match(clean_line):
            metrics['gates_2q'] += 1
        elif REGEX_MEASURE.match(clean_line):
            metrics['measures'] += 1
        
        # D. Verificação de Ponto e Vírgula (Sintaxe Básica)
        elif not clean_line.endswith(';'):
             # Ignorar se for a chave final da instrução 'if' (que é tratada como um gate)
             if not clean_line.endswith('}'):
                 print(f"🚫 ERRO (L{line_num}): Instrução não termina com ';'. -> {clean_line[:30]}...")
                 errors += 1

    # 3. Sumário e Métricas
    print("\n--- Sumário de Análise ---")
    if errors == 0:
        print("✅ Validação de Sintaxe Básica: OK")
    else:
        print(f"❌ Validação: Encontrados {errors} ERRO(S).")

    print("\n--- Métricas de Complexidade (Custo) ---")
    print(f"  Total de Qubits (N): {metrics['qreg_size']}")
    print(f"  Total de Instruções Operacionais: {metrics['instructions']}")
    print(f"  Portas de 1 Qubit (Custo Baixo): {metrics['gates_1q']}")
    print(f"  Portas de 2 Qubits (Custo Alto - CX/CZ): {metrics['gates_2q']}")
    
    if metrics['qreg_size'] > 0:
        fidelity_cost = (metrics['gates_1q'] * 0.001) + (metrics['gates_2q'] * 0.01)
        print(f"\n  Custo Estimado de Fidelidade (Exemplo): {fidelity_cost:.4f} (Baseado em Erro de Porta)")
    
    print("\n--- Fim da Análise ---")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EIEZ-QASM Linter & Complexity Analyzer')
    parser.add_argument('input', help='Caminho para o arquivo QASM a ser analisado (ex: compiled_bell.qasm)')
    args = parser.parse_args()

    lint_qasm(args.input)