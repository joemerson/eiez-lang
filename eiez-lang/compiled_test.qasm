OPENQASM 1.0;
include "qelib1.inc";
qreg q[4];
creg c[4];

// --- Custom Gates (EIEZ-QASM Definitions) ---
gate custom_op(theta) qarg_0, qarg_1 {
    rx(1.8000) qarg_0;
    rz(1.5000) qarg_1;
    ry(theta) qarg_0;
    cx qarg_0, qarg_1;
}
// -------------------------------------------

// EIEZ-QASM: OPTIMIZE alpha using TAU_MAX
// INJETADO: alpha = 1.8000 (Valor Ótimo ZIE)
// EIEZ-QASM: Gate Definition custom_op processed.
custom_op(0.7854) q[0], q[1];
custom_op(0.7854) q[1], q[2];
custom_op(0.7854) q[2], q[3];
custom_op(0.7854) q[3], q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];