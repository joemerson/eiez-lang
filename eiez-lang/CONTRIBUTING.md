# Contributing to EIEZ Lang

## How to contribute

1. Fork the repository
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run the examples to verify nothing is broken:
   ```
   python run.py examples\01_bell_state.eiez --shots 5
   python run.py examples\04_teleportation.eiez
   python benchmark.py
   ```
5. Open a Pull Request

## Adding new gates

Edit `src/eiez/lexer.py` to add the token, `src/eiez/parser.py` for the grammar rule,
and `src/eiez/simulator.py` to add the simulation logic.

## Adding new examples

Place `.eiez` files in `examples/` following the naming convention `NN_description.eiez`.

## Reporting bugs

Open an issue with the `.eiez` source that reproduces the problem and the full error output.
