# src/optimizer_fake.py
"""
Módulo de otimização 'fake' da linguagem EIEZ.

⚠️ Importante:
Este arquivo NÃO contém qualquer lógica real de otimização.
Ele apenas gera valores determinísticos com base no número de qubits.
Serve para demonstrar a keyword `optimize` sem expor nenhuma teoria real.

Regra:
- Recebe lista de qargs [(reg, idx), ...]
- Calcula valor com base em métricas simples e previsíveis
"""

from typing import Dict, List, Tuple

QArg = Tuple[str, int]


def fake_optimize_for_metric(qargs: List[QArg], metric: str) -> float:
    """
    Gera um valor 'fake' de otimização.

    qargs: lista [(reg, index), ...]
    metric: string da métrica (coherence, stability, balance, uniformity)

    Retorna float determinístico.
    """
    N = len(qargs)
    metric = metric.lower()

    if metric == "coherence":
        return round(0.45 * N, 4)

    if metric == "stability":
        return round(1.10 + 0.20 * N, 4)

    if metric == "balance":
        return round(0.50 * N, 4)

    if metric == "uniformity":
        return round(0.75, 4)

    # Caso métrica desconhecida
    return round(0.9, 4)


def apply_fake_optimizations(ir_program) -> Dict[str, float]:
    """
    Percorre o IR e aplica otimizações 'fake'.

    Retorna:
        { var_name : value }
    Exemplo:
        optimize q[0], q[1] using coherence as theta;
        -> {"theta": 0.9000}
    """
    result: Dict[str, float] = {}

    # ProgramIR tem .body (lista de statements)
    for stmt in getattr(ir_program, "body", []):
        classname = stmt.__class__.__name__

        # Caso 1: optimize direto
        if classname == "OptimizeStmt":
            val = fake_optimize_for_metric(stmt.qargs, stmt.metric)
            result[stmt.varname] = val

        # Caso 2: optimize dentro de gate declarations
        if classname == "GateDecl":
            for sub in stmt.body:
                if sub.__class__.__name__ == "OptimizeStmt":
                    val = fake_optimize_for_metric(sub.qargs, sub.metric)
                    result[sub.varname] = val

        # Caso 3: optimize dentro de loops
        if classname == "ForLoop":
            for sub in stmt.body:
                if sub.__class__.__name__ == "OptimizeStmt":
                    val = fake_optimize_for_metric(sub.qargs, sub.metric)
                    result[sub.varname] = val

    return result