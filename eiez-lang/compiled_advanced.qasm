OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];

// --- Custom Gates (EIEZ-QASM Definitions) ---
gate entangle qarg_0, qarg_1 {
    h qarg_0;
    cx qarg_0, qarg_1;
}
// -------------------------------------------

// EIEZ-QASM: Gate Definition entangle processed.
// EIEZ-QASM: Unrolling FOR i in 0 to 2
// LOOP ITER i = 0
entangle q[0], q[1];
// LOOP ITER i = 1
entangle q[1], q[2];
// LOOP ITER i = 2
entangle q[2], q[3];
// EIEZ-QASM: OPTIMIZE theta using EIE_RATIO
// INJETADO: theta = 1.5708 (Valor Ótimo ZIE)
rx(1.5708) q[0];
measure q[0] -> c[0];
if(c==1) x q[1];