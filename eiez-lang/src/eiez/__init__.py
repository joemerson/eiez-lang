# src/eiez/__init__.py
"""
EIEZ — Pacote do compilador da linguagem quântica EIEZ.

API pública:
    compile_source(source, backend="auto") -> str
    compile_file(input_path, output_path, backend="auto") -> None

O que NÃO é exposto publicamente:
    - _zie_engine   (motor interno, prefixo _ é intencional)
    - optimizer_interface internals
    - ir nodes (use apenas como tipos de retorno do parser se necessário)
"""

from .compiler import compile_source, compile_file

__all__ = ["compile_source", "compile_file"]
__version__ = "2.0.0"
