# eiez_compiler.py - COMPILADOR EIEZ-QASM (Versão Final Consolidada)

import ply.lex as lex
import ply.yacc as yacc
import sys
import argparse
import math
from zie_core import simulação_core_zie 

# =========================================================
# 2. LEXER (Analisador Léxico)
# =========================================================

reserved = {
    'EIEZ' : 'EIEZQASM', 
    'qreg' : 'QREG',
    'creg' : 'CREG',
    'measure': 'MEASURE',
    'if' : 'IF',
    'gate' : 'GATE_KEYWORD', 
    # Portas Built-in
    'h' : 'GATE_H', 'x' : 'GATE_X', 'y' : 'GATE_Y', 'z' : 'GATE_Z',
    'rx' : 'GATE_RX', 'ry' : 'GATE_RY', 'rz' : 'GATE_RZ',
    'cx' : 'GATE_CX', 'cz' : 'GATE_CZ',
    'barrier': 'BARRIER',
    
    # TOKENS DE OTIMIZAÇÃO:
    'optimize': 'OPTIMIZE',
    'using': 'USING',
    'as': 'AS',
    'EIE_RATIO': 'METRIC_EIE',
    'TAU_MAX': 'METRIC_TAU',
    
    # NOVOS TOKENS DE LOOP:
    'for': 'FOR_KEYWORD', 
    'in': 'IN_KEYWORD',
    'to': 'TO_KEYWORD'
}

tokens = [
    'ID', 'INT', 'FLOAT', 
    'LBRACKET', 'RBRACKET', 'LPAREN', 'RPAREN', 'SEMI', 'COMMA', 'ARROW', 
    'EQ',
    'LBRACE', 'RBRACE',
    'PLUS', 'MODULO' 
] + list(reserved.values())

t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_LBRACE   = r'\{'
t_RBRACE   = r'\}'
t_SEMI     = r';'
t_COMMA    = r','
t_ARROW    = r'->'
t_EQ       = r'=='
t_PLUS     = r'\+'
t_MODULO   = r'\%'

t_ignore   = ' \t'
t_ignore_comment = r'//.*'

def t_FLOAT(t):
    r'([0-9]+\.[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?'
    t.value = float(t.value)
    return t

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Erro Léxico: Caractere ilegal '{t.value[0]}' na linha {t.lexer.lineno}")
    t.lexer.skip(1)

lexer = lex.lex()

# =========================================================
# 3. PARSER (Analisador Sintático)
# =========================================================

precedence = (
    ('left', 'EQ'),
    ('left', 'PLUS'), 
    ('left', 'MODULO')
)

def p_program(p):
    """
    program : EIEZQASM FLOAT SEMI decl_section statement_list
    """
    p[0] = ('PROGRAM', p[2], p[4], p[5]) 

def p_decl_section(p):
    """
    decl_section : qreg_decl creg_decl
    """
    p[0] = (p[1], p[2])

def p_qreg_decl(p):
    """
    qreg_decl : QREG ID LBRACKET INT RBRACKET SEMI
    """
    p[0] = ('QREG_DECL', p[2], p[4])

def p_creg_decl(p):
    """
    creg_decl : CREG ID LBRACKET INT RBRACKET SEMI
    """
    p[0] = ('CREG_DECL', p[2], p[4])

def p_statement_list_recursive(p):
    """
    statement_list : statement statement_list
    """
    p[0] = [p[1]] + p[2]

def p_statement_list_base(p):
    """
    statement_list : statement
    """
    p[0] = [p[1]]

def p_statement(p):
    """
    statement : gate_stmt
              | measure_stmt
              | control_stmt
              | optimization_stmt
              | gate_declaration 
              | for_stmt
    """
    p[0] = p[1]

# --- FOR Statement ---
def p_for_stmt(p):
    """
    for_stmt : FOR_KEYWORD ID IN_KEYWORD INT TO_KEYWORD INT LBRACE statement_list RBRACE
    """
    loop_var = p[2]
    start = p[4]
    end = p[6]
    body = p[8]
    p[0] = ('FOR_STMT', loop_var, start, end, body)

# --- Gate Definition ---
def p_gate_declaration(p):
    """
    gate_declaration : GATE_KEYWORD ID LPAREN opt_param_list RPAREN formal_qarg_list LBRACE statement_list RBRACE
    """
    p[0] = ('GATE_DECL', p[2], p[4], p[6], p[8]) 

# CORRIGIDO: Permite que o argumento formal seja um 'qarg' (ID ou ID indexado)
def p_formal_qarg_list_recursive(p):
    """
    formal_qarg_list : qarg COMMA formal_qarg_list
    """
    p[0] = [p[1]] + p[3]

def p_formal_qarg_list_base(p):
    """
    formal_qarg_list : qarg
    """
    p[0] = [p[1]]
    
def p_opt_param_list_recursive(p):
    """
    opt_param_list : ID COMMA opt_param_list
    """
    p[0] = [p[1]] + p[3]
    
def p_opt_param_list_base(p):
    """
    opt_param_list : ID
    """
    p[0] = [p[1]]

def p_opt_param_list_empty(p):
    """
    opt_param_list : empty
    """
    p[0] = []

def p_empty(p):
    'empty :'
    pass

def p_control_stmt(p):
    """
    control_stmt : IF LPAREN ID LBRACKET INT RBRACKET EQ INT RPAREN statement
    """
    p[0] = ('CONTROL_STMT', p[3], p[5], p[8], p[10]) 

def p_optimization_stmt(p):
    """
    optimization_stmt : OPTIMIZE qarg_list USING metric_name AS ID SEMI
    """
    p[0] = ('OPTIMIZE_STMT', p[2], p[4], p[6])

def p_metric_name(p):
    """
    metric_name : METRIC_EIE
                | METRIC_TAU
    """
    p[0] = p[1]

def p_gate_stmt_no_param(p):
    """
    gate_stmt : gate_name qarg_list SEMI
    """
    p[0] = ('GATE', p[1], p[2], None) 

def p_gate_stmt_with_param(p):
    """
    gate_stmt : gate_name LPAREN expr RPAREN qarg_list SEMI
    """
    p[0] = ('GATE', p[1], p[5], p[3])

def p_gate_name(p):
    """
    gate_name : GATE_H
              | GATE_X 
              | GATE_Y 
              | GATE_Z
              | GATE_RX 
              | GATE_RY 
              | GATE_RZ
              | GATE_CX 
              | GATE_CZ 
              | BARRIER
              | ID
    """
    p[0] = p[1]

# --- Argumentos Quânticos (qarg) ---
def p_qarg_list_recursive(p):
    """
    qarg_list : qarg COMMA qarg_list
    """
    p[0] = [p[1]] + p[3]

def p_qarg_list_base(p):
    """
    qarg_list : qarg
    """
    p[0] = [p[1]]

def p_qarg(p):
    """
    qarg : ID LBRACKET exp_index RBRACKET
         | ID
    """
    if len(p) == 5:
        # q[i], q[0] (Argumento indexado)
        p[0] = ('QARG_INDEXED', p[1], p[3])
    else:
        # qb0 (Argumento formal/simples ID)
        p[0] = ('QARG_FORMAL', p[1], None)
    
# --- Expressão de Índice (Permite Parênteses e Aritmética Binária) ---
def p_exp_index(p):
    """
    exp_index : exp_index PLUS exp_index
              | exp_index MODULO exp_index
              | LPAREN exp_index RPAREN
              | ID
              | INT
    """
    if len(p) == 2: # ID ou INT
        p[0] = ('VAR', p[1]) if isinstance(p[1], str) else ('CONST', p[1])
    elif len(p) == 4 and p[1] == '(': # Agrupamento: ( exp_index )
        p[0] = p[2]
    elif len(p) == 4: # Operação Binária: exp_index OP exp_index
        op_type = {'+': 'ADD', '%': 'MOD'}.get(p[2])
        p[0] = (op_type, p[1], p[3])
    
def p_measure_stmt(p):
    """
    measure_stmt : MEASURE qarg ARROW ID LBRACKET INT RBRACKET SEMI
    """
    p[0] = ('MEASURE_STMT', p[2], p[4], p[6])
    
def p_expr_float(p):
    """
    expr : FLOAT
    """
    p[0] = p[1]

def p_expr_id(p):
    """
    expr : ID
    """
    p[0] = p[1] 

def p_expr_int(p):
    """
    expr : INT
    """
    p[0] = p[1]

def p_error(p):
    if p:
        input_data = p.lexer.lexdata
        line_start = input_data.rfind('\n', 0, p.lexpos) + 1
        line_end = input_data.find('\n', p.lexpos)
        if line_end == -1: line_end = len(input_data)
        line_content = input_data[line_start:line_end].strip()
        
        error_message = f"Erro de sintaxe perto de '{p.value}' (Token: {p.type}) na linha {p.lineno}.\n"
        error_message += f"Linha: {p.lineno}: {line_content}\n"
        error_message += " " * (p.lexpos - line_start) + "^"
        raise SyntaxError(error_message)
    else:
        raise SyntaxError("Erro de sintaxe no final do arquivo (EOF)")

parser = yacc.yacc()

def parse_eiez(data):
    """Processa o código EIEZ-QASM e retorna a AST."""
    lexer.input(data)
    return parser.parse(lexer=lexer) 

# =========================================================
# 4. TRADUTOR (Code Generator)
# =========================================================

class QASMGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.qasm_lines = []
        self.param_vars = {} 
        self.custom_gates = {}
        # NOVO: Mapa para argumentos formais do gate (chave: tuple AST, valor: nome string QASM)
        self.qarg_formal_map = {} 

    # --- Avaliador de Expressão de Índice ---
    def _evaluate_index_exp(self, exp_node, loop_var=None, current_index=0):
        node_type = exp_node[0]
        
        if node_type == 'CONST':
            return exp_node[1]
        
        elif node_type == 'VAR':
            var_name = exp_node[1]
            if var_name == loop_var:
                return current_index
            return 0 
            
        elif node_type == 'ADD':
            left = self._evaluate_index_exp(exp_node[1], loop_var, current_index)
            right = self._evaluate_index_exp(exp_node[2], loop_var, current_index)
            return left + right

        elif node_type == 'MOD':
            left = self._evaluate_index_exp(exp_node[1], loop_var, current_index)
            right = self._evaluate_index_exp(exp_node[2], loop_var, current_index)
            if right == 0:
                return 0 
            return left % right

        return 0

    # --- Formatador de Argumentos (Atualizado para Gate Body) ---
    def _format_qarg(self, qarg_node, loop_var=None, current_index=None):
        
        # 1. VERIFICAÇÃO DE ESCOPO LOCAL DO GATE (argumento formal)
        # Se o nó qarg for uma chave no mapa formal (estamos dentro de um corpo de gate)
        if qarg_node in self.qarg_formal_map:
             return self.qarg_formal_map[qarg_node]
        
        # 2. LÓGICA DE TRADUÇÃO NORMAL (fora do gate body ou para argumentos de chamada)
        node_type = qarg_node[0]
        reg_name = qarg_node[1]
        
        if node_type == 'QARG_FORMAL':
            return reg_name

        elif node_type == 'QARG_INDEXED':
            exp_node = qarg_node[2]
            
            if current_index is not None:
                index_value = self._evaluate_index_exp(exp_node, loop_var, current_index)
                return f"{reg_name}[{index_value}]"
            else:
                if exp_node[0] == 'CONST':
                    return f"{reg_name}[{exp_node[1]}]"
                elif exp_node[0] == 'VAR':
                    # Caso de q[i] fora de loop
                    return f"{reg_name}[0] // ERROR: Loop variable used outside FOR"

        return f"{reg_name}[???]"

    # --- Tradução de Gate Declaration ---
    def _translate_gate_declaration(self, statement):
        name, param_names, qarg_formal_nodes, body = statement[1:] # qarg_formal_nodes é uma lista de tuples AST
        
        # 1. Gera nomes simples para o cabeçalho QASM e constrói o mapa
        qarg_map = {}
        qasm_formal_names = []
        for i, qarg_node in enumerate(qarg_formal_nodes):
            formal_name = f"qarg_{i}" 
            qasm_formal_names.append(formal_name)
            qarg_map[qarg_node] = formal_name 

        param_str = f"({', '.join(param_names)})" if param_names else ""
        # Agora estamos fazendo join de strings (qarg_0, qarg_1, etc.), resolvendo o erro de tipagem anterior
        qarg_str = ", ".join(qasm_formal_names) 
        
        # 2. Gera o corpo do gate com o novo mapa
        body_generator = QASMGenerator(ast=('DUMMY',)) 
        body_generator.param_vars = self.param_vars.copy()
        # Passa o mapa de argumentos formais para a tradução do corpo
        body_generator.qarg_formal_map = qarg_map 
            
        for stmt in body:
            body_generator._translate_statement(stmt) 
            
        body_lines = [f"    {line.strip()}" for line in body_generator.qasm_lines if not line.startswith("//")]
        body_qasm = "\n".join(body_lines)

        qasm_def = f"gate {name}{param_str} {qarg_str} {{\n{body_qasm}\n}}"

        self.custom_gates[name] = qasm_def
        self.param_vars.update(body_generator.param_vars)
        self.qasm_lines.append(f"// EIEZ-QASM: Gate Definition {name} processed.")

    # --- Tradução do FOR (Unrolling) ---
    def _translate_for_stmt(self, statement):
        loop_var, start, end, body = statement[1:]
        
        self.qasm_lines.append(f"// EIEZ-QASM: Unrolling FOR {loop_var} in {start} to {end}")

        for i in range(start, end + 1):
            temp_generator = QASMGenerator(ast=('DUMMY',))
            temp_generator.param_vars = self.param_vars.copy()
            
            self.qasm_lines.append(f"// LOOP ITER {loop_var} = {i}")
            
            for inner_stmt in body:
                temp_generator._translate_statement(inner_stmt, loop_var, i)
            
            self.qasm_lines.extend(temp_generator.qasm_lines)


    def _translate_statement(self, statement, loop_var=None, current_index=None):
        node_type = statement[0]

        if node_type == 'FOR_STMT':
            self._translate_for_stmt(statement)
            return

        if node_type == 'GATE_DECL':
            self._translate_gate_declaration(statement)
            return

        elif node_type == 'OPTIMIZE_STMT':
            qarg_list = statement[1]
            metric = statement[2]
            param_id = statement[3]
            
            optimal_value = simulação_core_zie(qarg_list, metric)
            self.param_vars[param_id] = optimal_value 
            
            self.qasm_lines.append(f"// EIEZ-QASM: OPTIMIZE {param_id} using {metric}")
            self.qasm_lines.append(f"// INJETADO: {param_id} = {optimal_value:.4f} (Valor Ótimo ZIE)")

        elif node_type == 'GATE':
            token_name = statement[1]
            qarg_list = statement[2]
            param = statement[3]
            
            if token_name.startswith('GATE_'):
                gate_name = token_name.split('_', 1)[1].lower() 
            else:
                gate_name = token_name
            
            # CRUCIAL: Passa o contexto do loop/formal map para formatar os qargs
            qargs_str = ", ".join([self._format_qarg(qarg, loop_var, current_index) for qarg in qarg_list])
            
            param_val = None
            param_is_id = False 

            if param is not None:
                if isinstance(param, str):
                    if param in self.param_vars:
                        param_val = self.param_vars[param]
                    else:
                        param_val = param
                        param_is_id = True
                else:
                    param_val = param

            param_str = ""
            if param_val is not None:
                if param_is_id:
                    param_str = f"({param_val})"
                elif isinstance(param_val, (int, float)):
                    param_str = f"({param_val:.4f})"
                else:
                    param_str = f"({str(param_val)})"

            self.qasm_lines.append(f"{gate_name}{param_str} {qargs_str};")

        elif node_type == 'MEASURE_STMT':
            qarg = self._format_qarg(statement[1])
            c_id = statement[2]
            c_index = statement[3]
            self.qasm_lines.append(f"measure {qarg} -> {c_id}[{c_index}];")

        elif node_type == 'CONTROL_STMT':
            c_id = statement[1]
            c_value = statement[3]
            gate_stmt = statement[4]

            temp_generator = QASMGenerator(ast=('TEMP',))
            temp_generator.param_vars = self.param_vars.copy()
            # Garante que o formal map seja transferido para que as instruções internas sejam traduzidas corretamente
            temp_generator.qarg_formal_map = self.qarg_formal_map.copy() 
            temp_generator._translate_statement(gate_stmt, loop_var, current_index) 
            
            if temp_generator.qasm_lines:
                gate_line = temp_generator.qasm_lines[0].strip(';')
                self.qasm_lines.append(f"if({c_id}=={c_value}) {gate_line};") 
            else:
                self.qasm_lines.append(f"// if({c_id}[...]=={c_value}) <unsupported inner stmt>")

    def generate(self):
        if not self.ast or self.ast[0] != 'PROGRAM':
            return "// Erro de Parsing - AST inválida ou vazia."

        version = self.ast[1]
        qreg_decl = self.ast[2][0] 
        creg_decl = self.ast[2][1] 
        statement_list = self.ast[3]
        
        final_lines = [
            f"OPENQASM {version:.1f};",
            'include "qelib1.inc";',
            f"qreg {qreg_decl[1]}[{qreg_decl[2]}];",
            f"creg {creg_decl[1]}[{creg_decl[2]}];",
            ""
        ]
        
        for stmt in statement_list:
            self._translate_statement(stmt) 
        
        if self.custom_gates:
            final_lines.append("// --- Custom Gates (EIEZ-QASM Definitions) ---")
            for definition in self.custom_gates.values():
                final_lines.append(definition)
            final_lines.append("// -------------------------------------------")
            final_lines.append("")
            
        final_lines.extend(self.qasm_lines)

        final_output = [line for i, line in enumerate(final_lines) if line.strip() or i == 0 or final_lines[i-1].strip()]
        
        return "\n".join(final_output)

# =========================================================
# 5. EXECUÇÃO DA INTERFACE DE LINHA DE COMANDO (CLI)
# =========================================================

def compile_file(input_path: str, output_path: str):
    """Lê o arquivo de entrada, compila e salva no arquivo de saída."""
    try:
        with open(input_path, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo de entrada não encontrado: {input_path}")
        sys.exit(1)

    # 1. Parse (Análise)
    try:
        ast = parse_eiez(source)
    except SyntaxError as e:
        print(f"❌ Erro de Parsing: {e}")
        sys.exit(1)
        
    if not ast:
        print("❌ Erro de Compilação: AST vazia após o parsing.")
        sys.exit(1)

    # 2. Tradução e Otimização ZIE (Geração de Código)
    generator = QASMGenerator(ast)
    try:
        qasm_output = generator.generate()
    except Exception as e:
        print(f"❌ Erro de Execução/Geração: {e}")
        sys.exit(1)

    
    # 3. Saída (Gravação)
    try:
        with open(output_path, "w") as out:
            out.write(qasm_output)
        
        injetados = {k: f"{v:.4f}" for k, v in generator.param_vars.items()}
        print(f"✅ Compilado '{input_path}' -> '{output_path}'")
        if injetados:
            print("\nParâmetros ZIE injetados (Otimizador):")
            for k, v in injetados.items():
                print(f"  {k} = {v}")

    except IOError:
        print(f"❌ ERRO: Não foi possível salvar o arquivo '{output_path}'.")
        sys.exit(1)
    

if __name__ == '__main__':
    cli_parser = argparse.ArgumentParser(description='EIEZ-QASM Compiler (Versão Unificada)')
    cli_parser.add_argument('input', help='arquivo de entrada .eiez (ex: examples/bell.eiez)')
    cli_parser.add_argument('-o', '--output', default='compiled_circuit.qasm', help='arquivo de saída qasm (ex: compiled_bell.qasm)')
    args = cli_parser.parse_args()

    compile_file(args.input, args.output)