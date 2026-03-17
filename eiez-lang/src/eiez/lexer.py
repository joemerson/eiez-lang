# eiez-lang/src/eiez/lexer.py
import ply.lex as lex

reserved = {
    'EIEZ':     'EIEZ',
    'qreg':     'QREG',
    'creg':     'CREG',
    'gate':     'GATE',
    'optimize': 'OPTIMIZE',
    'using':    'USING',
    'as':       'AS',
    'for':      'FOR',
    'in':       'IN',
    'range':    'RANGE',
    'to':       'TO',
    'measure':  'MEASURE',
    'if':       'IF',
}

tokens = list(dict.fromkeys([
    'ID', 'INT', 'FLOAT',
    'LBRACKET', 'RBRACKET',
    'LPAREN',   'RPAREN',
    'LBRACE',   'RBRACE',
    'COMMA', 'SEMI', 'ARROW', 'EQ',
] + list(reserved.values())))

t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_LBRACE   = r'\{'
t_RBRACE   = r'\}'
t_COMMA    = r','
t_SEMI     = r';'
t_ARROW    = r'->'
t_EQ       = r'=='
t_ignore   = ' \t\r'

def t_FLOAT(t):
    r'[0-9]+\.[0-9]+'
    t.value = float(t.value)
    return t

def t_INT(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_COMMENT(t):
    r'//.*'
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise SyntaxError(f"Caractere ilegal: '{t.value[0]}' na linha {t.lexer.lineno}")

def build_lexer():
    return lex.lex()
