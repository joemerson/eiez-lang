# EIEZ Lang — Compilador de Circuitos Quânticos

Linguagem de programação quântica que compila para OpenQASM 2.0.

## Instalação (Windows)

**Requisito:** Python 3.9+

```bat
pip install ply
```

Só isso. Sem mais dependências.

## Como rodar

```bat
cd eiez-lang
python run.py examples\01_bell_state.eiez
python run.py examples\02_optimize_gate.eiez --backend zie
python run.py examples\03_for_loop_4qubits.eiez
python run.py examples\04_teleportation.eiez
```

## Opções

| Flag | Descrição |
|------|-----------|
| `--backend auto` | Usa motor interno se disponível (padrão) |
| `--backend null` | Sem motor — compila sem otimização |
| `--backend zie`  | Exige motor interno |
| `--shots N`      | Executa N vezes (qubits são probabilísticos!) |
| `-o saida.qasm`  | Salva o QASM gerado |
| `--qasm-only`    | Só mostra o QASM, sem simular |

## Exemplos

```bat
:: Bell State — 2 qubits entrelaçados
python run.py examples\01_bell_state.eiez --shots 5

:: Gate customizado com parâmetro otimizado
python run.py examples\02_optimize_gate.eiez --backend zie

:: Loop FOR em 4 qubits
python run.py examples\03_for_loop_4qubits.eiez --shots 3

:: Teleportação quântica
python run.py examples\04_teleportation.eiez

:: Só gerar o QASM sem simular
python run.py examples\01_bell_state.eiez --qasm-only -o bell.qasm
```

## Estrutura do projeto

```
eiez-lang/
├── run.py                      ← ponto de entrada
├── examples/
│   ├── 01_bell_state.eiez
│   ├── 02_optimize_gate.eiez
│   ├── 03_for_loop_4qubits.eiez
│   └── 04_teleportation.eiez
└── src/
    └── eiez/
        ├── __init__.py
        ├── compiler.py
        ├── lexer.py
        ├── parser.py
        ├── ir.py
        ├── optimizer_interface.py
        ├── generator_qasm.py
        ├── simulator.py
        └── _zie_engine.py      ← motor interno (não publicar no open source)
```

## Sintaxe da linguagem

```
EIEZ 2.0;

qreg q[4];
creg c[4];

// Gates básicos
h q[0];
x q[1];
rx(1.5708) q[2];
cx q[0], q[1];

// Loop
for i in range 0 to 4 {
    h q[i];
}

// Otimização
optimize q[0], q[1] using coherence as theta;

// Gate customizado
gate mygate(theta) qa, qb {
    h qa;
    rx(theta) qb;
}

// Condicional
if(c[0]==1) x q[1];

// Medição
measure q[0] -> c[0];
```
