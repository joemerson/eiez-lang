# \# EIEZ-QASM — Documentação Oficial

# 

# Bem-vindo à documentação da \*\*EIEZ-QASM\*\*, uma linguagem aberta e modular para

# representação e compilação de circuitos quânticos.

# 

# Este repositório contém \*\*apenas a linguagem\*\*, sua gramática, ferramentas de

# compilação e exemplos.

# Não inclui qualquer informação técnica protegida por patente ou segredo industrial, garantindo o modelo Open Core.

# 

# ---

# 

# \## Objetivo da Linguagem

# 

# A EIEZ-QASM foi criada para ser:

# 

# \- \*\*Simples\*\* — sintaxe clara e próxima de linguagens já conhecidas.

# \- \*\*Determinística\*\* — cada instrução tem tradução direta em QASM.

# \- \*\*Extensível\*\* — comandos e regras podem ser expandidos (para QFUNC, QFOR, etc.).

# \- \*\*Independente de hardware\*\* — não depende de chips, arquiteturas ou implementações físicas (facilita a portabilidade).

# 

# A EIEZ-QASM é adequada para:

# 

# \- Criar protótipos de circuitos quânticos.

# \- Gerar QASM de forma programática.

# \- Integrar sistemas educacionais.

# \- Testes de compiladores.

# \- Desenvolvimento de simuladores independentes.

# 

# Estrutura:



# 📂 ./

# &nbsp;   📄 CONTRIBUIR.txt

# &nbsp;   📄 LICENSE.txt

# &nbsp;   📄 logo.png

# &nbsp;   📄 logo.svg

# &nbsp;   📄 map\_project\_structure.py

# &nbsp;   📄 Novo(a) Documento de Texto.txt

# &nbsp;   📄 project\_map.txt

# &nbsp;   📄 README.md

# &nbsp;   📄 ROADMAP.md

# &nbsp;   📂 doc/

# &nbsp;       📄 index.md

# &nbsp;       📄 Testes de exemplo.txt

# &nbsp;   📂 examples/

# &nbsp;       📄 advanced\_test.eiez

# &nbsp;       📄 bell.eiez

# &nbsp;       📄 compiled\_looped.eiez

# &nbsp;       📄 compiled\_test.qasm

# &nbsp;       📄 complex\_test.eiez

# &nbsp;       📄 looped\_test.eiez

# &nbsp;       📄 stress\_superposition.eiez

# &nbsp;   📂 src/

# &nbsp;       📄 eiez\_compiler.py

# &nbsp;       📄 generator\_qasm.py

# &nbsp;       📄 ir.py

# &nbsp;       📄 lexer.py

# &nbsp;       📄 optimizer\_fake.py

# &nbsp;       📄 parser.py

# &nbsp;       📄 parsetab.py

# &nbsp;       📄 qasm\_linter.py

# &nbsp;       📄 zie\_core.py

