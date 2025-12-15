# EIEZ Language - Parser (produces IR nodes)
import ply.yacc as yacc
# CORREÇÃO: Importações Relativas
from .lexer import build_lexer
from . import ir

# Tokens are provided by lexer
lexer = build_lexer()
tokens = lexer.tokens if hasattr(lexer, 'tokens') else []

# Precedence (not much needed here)
precedence = (
    ('left', 'EQ'),
)

# --- Grammar rules ---

def p_program(p):
    'program : EIEZ FLOAT SEMI decl_section statement_list'
    version = p[2]
    qreg_decl, creg_decl = p[4]
    program = ir.ProgramIR(version, qreg_decl, creg_decl)
    for stmt in p[5]:
        program.body.append(stmt)
    p[0] = program


def p_decl_section(p):
    'decl_section : qreg_decl creg_decl'
    p[0] = (p[1], p[2])


def p_qreg_decl(p):
    'qreg_decl : QREG ID LBRACKET INT RBRACKET SEMI'
    p[0] = ir.QRegDecl(p[2], p[4])


def p_creg_decl(p):
    'creg_decl : CREG ID LBRACKET INT RBRACKET SEMI'
    p[0] = ir.CRegDecl(p[2], p[4])


def p_statement_list_recursive(p):
    'statement_list : statement statement_list'
    p[0] = [p[1]] + p[2]


def p_statement_list_base(p):
    'statement_list : statement'
    p[0] = [p[1]]


def p_statement(p):
    '''statement : gate_call
                 | gate_decl
                 | measure_stmt
                 | control_stmt
                 | optimization_stmt
                 | for_loop_stmt'''
    p[0] = p[1]

# --- Gate call (with optional parameter) ---

def p_gate_call_no_param(p):
    'gate_call : ID qarg_list SEMI'
    name = p[1]
    p[0] = ir.GateCall(name, params=[], qargs=p[2])


def p_gate_call_param(p):
    'gate_call : ID LPAREN param_value RPAREN qarg_list SEMI'
    name = p[1]
    p[0] = ir.GateCall(name, params=[p[3]], qargs=p[5])


def p_param_value(p):
    '''param_value : FLOAT
                   | ID'''
    p[0] = p[1]

# --- qarg list ---

def p_qarg_list_recursive(p):
    'qarg_list : qarg COMMA qarg_list'
    p[0] = [p[1]] + p[3]


def p_qarg_list_base(p):
    'qarg_list : qarg'
    p[0] = [p[1]]


def p_qarg(p):
    'qarg : ID LBRACKET INT RBRACKET'
    p[0] = (p[1], p[3])

# --- Measure ---

def p_measure_stmt(p):
    'measure_stmt : MEASURE qarg ARROW qarg SEMI'
    p[0] = ir.Measure(p[2], p[4])

# --- Control (if) ---

def p_control_stmt(p):
    'control_stmt : IF LPAREN ID LBRACKET INT RBRACKET EQ INT RPAREN gate_call'
    creg = p[3]
    index = p[5]
    value = p[8]
    stmt = p[10]
    p[0] = ir.IfStmt(creg, index, value, stmt)

# --- Optimize ---

def p_optimization_stmt(p):
    'optimization_stmt : OPTIMIZE qarg_list USING ID AS ID SEMI'
    qargs = p[2]
    metric = p[4]
    out_var = p[6]
    p[0] = ir.OptimizeStmt(qargs, metric, out_var)

# --- Gate declaration ---

def p_gate_decl(p):
    'gate_decl : GATE ID LPAREN opt_param_list RPAREN qarg_list LBRACE statement_list RBRACE'
    name = p[2]
    params = p[4]
    qargs = p[6]
    body = p[8]
    p[0] = ir.GateDecl(name, params, qargs, body)


def p_opt_param_list_recursive(p):
    'opt_param_list : ID COMMA opt_param_list'
    p[0] = [p[1]] + p[3]


def p_opt_param_list_base(p):
    'opt_param_list : ID'
    p[0] = [p[1]]


def p_opt_param_list_empty(p):
    'opt_param_list : '
    p[0] = []

# --- For loop ---

def p_for_loop_stmt(p):
    'for_loop_stmt : FOR ID IN RANGE INT TO INT LBRACE statement_list RBRACE'
    var = p[2]
    start = p[4]
    end = p[6]
    body = p[8]
    p[0] = ir.ForLoop(var, start, end, body)

# --- Error handling ---

def p_error(p):
    if p:
        raise SyntaxError(f"Syntax error at token {p.type} ({p.value}) line {p.lineno}")
    else:
        raise SyntaxError("Syntax error at EOF")

# Build parser

def build_parser():
    return yacc.yacc()

# Helper parse function

def parse(source):
    lex = build_lexer()
    parser = build_parser()
    return parser.parse(source, lexer=lex)