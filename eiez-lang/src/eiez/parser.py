# eiez-lang/src/eiez/parser.py
import ply.yacc as yacc
from .lexer import build_lexer, tokens   # noqa: F401
from . import ir

_lexer = build_lexer()

precedence = (
    ('left', 'EQ'),
)

def p_program(p):
    'program : EIEZ FLOAT SEMI qreg_decl creg_decl statement_list'
    p[0] = ir.ProgramIR(version=p[2], qreg=p[4], creg=p[5], body=p[6])

def p_qreg_decl(p):
    'qreg_decl : QREG ID LBRACKET INT RBRACKET SEMI'
    p[0] = ir.QRegDecl(p[2], p[4])

def p_creg_decl(p):
    'creg_decl : CREG ID LBRACKET INT RBRACKET SEMI'
    p[0] = ir.CRegDecl(p[2], p[4])

def p_statement_list_multi(p):
    'statement_list : statement statement_list'
    p[0] = [p[1]] + p[2]

def p_statement_list_single(p):
    'statement_list : statement'
    p[0] = [p[1]]

def p_statement(p):
    '''statement : gate_call
                 | gate_decl
                 | measure_stmt
                 | if_stmt
                 | optimize_stmt
                 | for_loop'''
    p[0] = p[1]

# Gate call
def p_gate_call_no_param(p):
    'gate_call : ID qarg_list SEMI'
    p[0] = ir.GateCall(p[1], [], p[2])

def p_gate_call_with_param(p):
    'gate_call : ID LPAREN param_value RPAREN qarg_list SEMI'
    p[0] = ir.GateCall(p[1], [p[3]], p[5])

def p_param_value_float(p):
    'param_value : FLOAT'
    p[0] = p[1]

def p_param_value_id(p):
    'param_value : ID'
    p[0] = p[1]

# Qargs — aceita q[0] (INT) e q[i] (ID/variavel de loop)
def p_qarg_list_multi(p):
    'qarg_list : qarg COMMA qarg_list'
    p[0] = [p[1]] + p[3]

def p_qarg_list_single(p):
    'qarg_list : qarg'
    p[0] = [p[1]]

def p_qarg_int(p):
    'qarg : ID LBRACKET INT RBRACKET'
    p[0] = (p[1], p[3])

def p_qarg_var(p):
    'qarg : ID LBRACKET ID RBRACKET'
    p[0] = (p[1], p[3])   # indice eh variavel (ex: q[i] dentro de for)

# Measure
def p_measure_stmt(p):
    'measure_stmt : MEASURE qarg ARROW qarg SEMI'
    p[0] = ir.Measure(p[2], p[4])

# If
def p_if_stmt(p):
    'if_stmt : IF LPAREN ID LBRACKET INT RBRACKET EQ INT RPAREN gate_call'
    p[0] = ir.IfStmt(p[3], p[5], p[8], p[10])

# Optimize
def p_optimize_stmt(p):
    'optimize_stmt : OPTIMIZE qarg_list USING ID AS ID SEMI'
    p[0] = ir.OptimizeStmt(p[2], p[4], p[6])

# Gate declaration — qargs formais sao nomes simples (sem indice)
def p_gate_decl(p):
    'gate_decl : GATE ID LPAREN opt_param_list RPAREN formal_qarg_list LBRACE statement_list RBRACE'
    p[0] = ir.GateDecl(p[2], p[4], p[6], p[8])

def p_formal_qarg_list_multi(p):
    'formal_qarg_list : ID COMMA formal_qarg_list'
    p[0] = [p[1]] + p[3]

def p_formal_qarg_list_single(p):
    'formal_qarg_list : ID'
    p[0] = [p[1]]

def p_opt_param_list_multi(p):
    'opt_param_list : ID COMMA opt_param_list'
    p[0] = [p[1]] + p[3]

def p_opt_param_list_single(p):
    'opt_param_list : ID'
    p[0] = [p[1]]

def p_opt_param_list_empty(p):
    'opt_param_list : '
    p[0] = []

# For loop — qarg dentro aceita q[i] via p_qarg_var acima
def p_for_loop(p):
    'for_loop : FOR ID IN RANGE INT TO INT LBRACE statement_list RBRACE'
    p[0] = ir.ForLoop(p[2], p[5], p[7], p[9])

def p_error(p):
    if p:
        raise SyntaxError(
            f"Erro de sintaxe: token '{p.value}' ({p.type}) na linha {p.lineno}"
        )
    raise SyntaxError("Erro de sintaxe: fim de arquivo inesperado")

def build_parser():
    return yacc.yacc(debug=False, write_tables=False)

def parse(source: str) -> ir.ProgramIR:
    lex = build_lexer()
    parser = build_parser()
    result = parser.parse(source, lexer=lex)
    if result is None:
        raise SyntaxError("Parser retornou vazio.")
    return result
