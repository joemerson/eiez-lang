# EIEZ-LANG — A Minimal Quantum Scripting Language

EIEZ-LANG is an open-source, minimalist quantum scripting language designed
to be simple, expressive, and fully safe to publish.  
It acts as a demonstration DSL (Domain Specific Language) that compiles to
**OpenQASM 2.0**, enabling experimentation and educational usage.

⚠️ **Important Notice**  
This project is intentionally lightweight and does **not**
include any proprietary algorithms, formulas, theoretical mechanisms, or
patented concepts related to EIE/ZIE or any advanced models.  
All optimization logic included in this repository is **fake**, deterministic,
and serves only as a placeholder for the community version.

_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_

# EIEZ-LANG — Uma Linguagem de Script Quântico Minimalista

EIEZ-LANG é uma linguagem de script quântico minimalista e de código 
aberto, projetada para ser simples, expressiva e totalmente segura para
publicação.

Ela funciona como uma DSL (Linguagem de Domínio Específico) de 
demonstração que compila para OpenQASM 2.0, permitindo experimentação
e uso educacional.

⚠️ **Aviso Importante**
Este projeto é intencionalmente leve e não inclui algoritmos proprietários,
fórmulas, mecanismos teóricos ou conceitos patenteados relacionados a EIE/ZIE
ou quaisquer modelos avançados.

Toda a lógica de otimização incluída neste repositório é fictícia, determinística
e serve apenas como um marcador para a versão da comunidade.

---

## Estrutura do Repositório
📂 ./
    📄 CONTRIBUIR.txt
    📄 LICENSE.txt
    📄 logo.png
    📄 logo.svg
    📄 map_project_structure.py
    📄 Novo(a) Documento de Texto.txt
    📄 project_map.txt
    📄 README.md
    📄 ROADMAP.md
    📂 doc/
        📄 index.md
        📄 Testes de exemplo.txt
    📂 examples/
        📄 advanced_test.eiez
        📄 bell.eiez
        📄 compiled_looped.eiez
        📄 compiled_test.qasm
        📄 complex_test.eiez
        📄 looped_test.eiez
        📄 stress_superposition.eiez
    📂 src/
        📄 eiez_compiler.py
        📄 generator_qasm.py
        📄 ir.py
        📄 lexer.py
        📄 optimizer_fake.py
        📄 parser.py
        📄 parsetab.py
        📄 qasm_linter.py
        📄 zie_core.py