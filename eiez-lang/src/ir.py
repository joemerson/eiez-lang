# src/ir.py
# IR (Intermediate Representation) for EIEZ-LANG

class IRNode:
    """Base para todos os nós da IR."""
    def to_dict(self):
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, IRNode):
                out[k] = v.to_dict()
            elif isinstance(v, list):
                out[k] = [i.to_dict() if isinstance(i, IRNode) else i for i in v]
            else:
                out[k] = v
        return out

class Decls(IRNode):
    """Container para declarações de registradores (qreg / creg)."""
    def __init__(self, qreg=None, creg=None):
        self.qreg = qreg
        self.creg = creg

class ProgramIR(IRNode):
    def __init__(self, version, decls=None, statements=None):
        self.version = version
        self.decls = decls if decls is not None else Decls()
        self.statements = statements if statements is not None else []

class QRegDecl(IRNode):
    def __init__(self, name, size):
        self.name = name
        self.size = size

class CRegDecl(IRNode):
    def __init__(self, name, size):
        self.name = name
        self.size = size

class QArg(IRNode):
    def __init__(self, reg, index):
        self.reg = reg
        self.index = index

class GateCall(IRNode):
    def __init__(self, name, params, qargs):
        self.name = name
        self.params = params or []
        self.qargs = qargs or []

class GateDecl(IRNode):
    def __init__(self, name, params, qargs, body):
        self.name = name
        self.params = params or []
        self.qargs = qargs or []
        self.body = body or []

class Measure(IRNode):
    def __init__(self, qarg, carg):
        self.qarg = qarg
        self.carg = carg

class IfStmt(IRNode):
    def __init__(self, creg, index, value, body):
        self.creg = creg
        self.index = index
        self.value = value
        # body is expected to be a single statement (e.g., GateCall)
        self.body = body

class OptimizeStmt(IRNode):
    def __init__(self, qargs, metric, varname):
        self.qargs = qargs or []
        self.metric = metric
        self.varname = varname

class ForLoop(IRNode):
    def __init__(self, var, start, end, body):
        self.var = var
        self.start = start
        self.end = end
        self.body = body or []