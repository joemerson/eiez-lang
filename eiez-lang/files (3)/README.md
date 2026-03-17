# ⚛ EIEZ Lang

**A quantum circuit programming language that compiles to OpenQASM 2.0.**

Write quantum circuits in a clean, expressive syntax — compile to industry-standard QASM, simulate locally, and scale to thousands of qubits.

```
EIEZ 2.0;

qreg q\[2];
creg c\[2];

h q\[0];
cx q\[0], q\[1];

measure q\[0] -> c\[0];
measure q\[1] -> c\[1];
```

```
OPENQASM 2.0;
include "qelib1.inc";
qreg q\[2];
creg c\[2];

h q\[0];
cx q\[0], q\[1];
measure q\[0] -> c\[0];
measure q\[1] -> c\[1];
```

\---

## Features

* **Clean syntax** — readable quantum circuits with `for` loops, custom gates, and conditionals
* **OpenQASM 2.0 output** — compatible with IBM Qiskit, Qiskit Runtime, and real quantum hardware
* **Built-in simulator** — statevector simulation for small circuits (exact)
* **Large-scale simulator** — simulate 5000+ qubits instantly via per-qubit approximation
* **Optimization layer** — `optimize` keyword injects computed parameters into gate calls
* **Pluggable backend** — optimization engine is fully abstracted; swap engines without touching the compiler

\---

## Benchmark

Simulated on a standard Windows laptop:

|Qubits|Possible States|Gates|Time (avg)|
|-|-|-|-|
|100|10^30|110|0.16 ms|
|500|10^150|510|0.36 ms|
|1,000|10^301|1,010|0.54 ms|
|2,000|10^602|2,010|1.86 ms|
|3,000|10^903|3,010|3.54 ms|
|5,000|10^1505|5,010|3.47 ms|

> 5,000 qubits · 10^1505 possible states · 3.4ms · zero cloud dependency

\---

## Installation

**Requirements:** Python 3.9+

```bat
pip install ply
```

That's it. No other dependencies.

\---

## Quick Start

```bat
git clone https://github.com/your-username/eiez-lang
cd eiez-lang

:: Bell State — 2 entangled qubits
python run.py examples\\01\_bell\_state.eiez --shots 5

:: Quantum Teleportation
python run.py examples\\04\_teleportation.eiez

:: 4 qubits in superposition
python run.py examples\\03\_for\_loop\_4qubits.eiez --shots 3

:: Benchmark 100 → 5000 qubits
python benchmark.py
```

\---

## Language Reference

### Program structure

```
EIEZ 2.0;

qreg <name>\[<size>];
creg <name>\[<size>];

<statements>
```

### Built-in gates

|Gate|Description|
|-|-|
|`h`|Hadamard — superposition|
|`x`|Pauli-X — bit flip|
|`y`|Pauli-Y|
|`z`|Pauli-Z — phase flip|
|`rx(θ)`|Rotation around X axis|
|`ry(θ)`|Rotation around Y axis|
|`rz(θ)`|Rotation around Z axis|
|`cx`|CNOT — entanglement|
|`cz`|Controlled-Z|

### Custom gates

```
gate mygate(theta) qa, qb {
    h qa;
    rx(theta) qb;
    cx qa, qb;
}

mygate(theta) q\[0], q\[1];
```

### For loops

```
for i in range 0 to 4 {
    h q\[i];
}
```

### Optimize keyword

```
optimize q\[0], q\[1] using coherence as theta;
rx(theta) q\[0];
```

Supported metrics: `coherence`, `stability`, `balance`, `uniformity`

### Conditionals

```
measure q\[0] -> c\[0];
if(c\[0]==1) x q\[1];
```

### Measurement

```
measure q\[0] -> c\[0];
```

\---

## CLI Options

### run.py — compile + simulate

```
python run.py <file.eiez> \[options]

Options:
  -o <file.qasm>          save QASM output
  --backend auto|null|zie optimization backend (default: auto)
  --shots N               run N times (quantum is probabilistic!)
  --qasm-only             print QASM only, skip simulation
```

### run\_large.py — large-scale simulation

```
python run\_large.py <file.eiez> \[options]

Options:
  --backend auto|null|zie
  --shots N
```

### benchmark.py — performance benchmark

```
python benchmark.py \[options]

Options:
  --sizes 100 500 1000    qubit counts to benchmark
  --shots N               shots per size (default: 3)
  --backend auto|null|zie
  -o report.html          output report file
```

\---

## Project Structure

```
eiez-lang/
├── run.py                 compile + simulate (small circuits)
├── run\_large.py           simulate large circuits (1000+ qubits)
├── benchmark.py           performance benchmark + HTML report
├── examples/
│   ├── 01\_bell\_state.eiez
│   ├── 02\_optimize\_gate.eiez
│   ├── 03\_for\_loop\_4qubits.eiez
│   ├── 04\_teleportation.eiez
│   └── 05\_100qubits.eiez
└── src/
    └── eiez/
        ├── \_\_init\_\_.py         public API: compile\_source(), compile\_file()
        ├── compiler.py         CLI orchestrator
        ├── lexer.py            tokenizer (PLY)
        ├── parser.py           grammar → IR nodes
        ├── ir.py               intermediate representation
        ├── optimizer\_interface.py  backend abstraction layer (ABC)
        ├── generator\_qasm.py   IR → OpenQASM 2.0
        └── simulator.py        statevector simulator
```

> `\_zie\_engine.py` — optimization engine (not included in this repository)

\---

## Architecture

The compiler is built in clean, separated layers:

```
.eiez source
    └── lexer.py       → tokens
    └── parser.py      → ProgramIR
    └── optimizer\_interface.py  → resolves optimize stmts (via backend)
    └── generator\_qasm.py       → OpenQASM 2.0 string
```

The optimization backend is fully decoupled via an abstract interface (`OptimizerBackend`). The compiler never imports the engine directly — it only calls `.compute(qargs, metric)` on the interface. This means:

* The language works standalone with `--backend null`
* The engine can be replaced without touching the compiler
* The engine source is never exposed in the public repository

\---

## Examples

### Bell State (entanglement)

```
EIEZ 2.0;
qreg q\[2];
creg c\[2];

h q\[0];
cx q\[0], q\[1];

measure q\[0] -> c\[0];
measure q\[1] -> c\[1];
```

Result over 5 shots: always `00` or `11`, never `01` or `10`.
That is quantum entanglement.

### Quantum Teleportation

```
EIEZ 2.0;
qreg q\[3];
creg c\[3];

rx(1.5708) q\[0];      // state to teleport
h q\[1];
cx q\[1], q\[2];        // Bell pair: Alice + Bob

cx q\[0], q\[1];        // Alice's operations
h q\[0];
measure q\[0] -> c\[0];
measure q\[1] -> c\[1];

if(c\[0]==1) x q\[2];   // Bob's corrections
if(c\[1]==1) z q\[2];

measure q\[2] -> c\[2];
```

\---

## License

MIT License — see [LICENSE](LICENSE)

\---

*Created by Joemerson da Silva Lima — Electrical Engineer*

