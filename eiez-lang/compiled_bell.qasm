OPENQASM 1.0;
include "qelib1.inc";
qreg q[2];
creg c[2];

// --- Custom Gates (EIEZ-QASM Definitions) ---
gate ENTANGLE qarg_0, qarg_1 {
    h qarg_0;
    cx qarg_0, qarg_1;
}
// -------------------------------------------

// EIEZ-QASM: OPTIMIZE theta using TAU_MAX
// INJETADO: theta = 1.5200 (Valor Ótimo ZIE)
// EIEZ-QASM: Gate Definition ENTANGLE processed.
ENTANGLE q[0], q[1];
rx(1.5200) q[0];
measure q[0] -> c[0];