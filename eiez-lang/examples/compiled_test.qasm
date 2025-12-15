OPENQASM 1.0;
include "qelib1.inc";
qreg q[4];
creg c[4];

// --- Custom Gates (EIEZ-QASM Definitions) ---
gate custom_op(theta) qb0, qb1 {
    // EIEZ-QASM: OPTIMIZE qb0, qb1 using EIE_RATIO
    // INJETADO: beta = 1.5000 (Valor Ótimo ZIE)
    rx(1.8000) qb0; 
    rz(1.5000) qb1;
    ry(theta) qb0;
    cx qb0, qb1;
}
// -------------------------------------------

// EIEZ-QASM: OPTIMIZE q[0], q[1], q[2], q[3] using TAU_MAX
// INJETADO: alpha = 1.8000 (Valor Ótimo ZIE)

custom_op(0.7854) q[0], q[1];
custom_op(0.7854) q[1], q[2];
custom_op(0.7854) q[2], q[3];
custom_op(0.7854) q[3], q[0]; // Conexão cíclica ou final da cadeia