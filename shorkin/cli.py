"""CLI entry point for shorkin."""

from __future__ import annotations

import argparse
import sys

from shorkin.classical.order_finder import find_order as classical_find_order
from shorkin.display import print_error, print_info, print_result
from shorkin.factor import factor
from shorkin.quantum.order_finder import QuantumOrderFinder, qubits_needed


class ClassicalOrderFinderAdapter:
    """Adapter to match the OrderFinder protocol for the classical finder."""

    method_name = "classical"

    def find_order(self, x: int, n: int) -> int | None:
        return classical_find_order(x, n)


def _resolve_mode(n: int, mode: str, max_qubits: int, force: bool) -> str:
    """Decide whether to use quantum or classical mode."""
    if mode == "quantum":
        needed = qubits_needed(n)
        if needed > max_qubits and not force:
            print_error(
                f"N={n} requires {needed} qubits (limit: {max_qubits}). "
                f"Use --force to try anyway, or --mode classical."
            )
            sys.exit(1)
        return "quantum"

    if mode == "classical":
        return "classical"

    # Auto mode
    needed = qubits_needed(n)
    if needed <= max_qubits:
        return "quantum"
    return "classical"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shorkin",
        description="Factor integers using Shor's algorithm (quantum simulation via Cirq)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # factor subcommand
    factor_parser = subparsers.add_parser("factor", help="Factor a composite integer")
    factor_parser.add_argument("n", type=int, help="The composite integer to factor")
    _add_common_args(factor_parser)

    # factor-key subcommand
    key_parser = subparsers.add_parser("factor-key", help="Factor the modulus from an RSA PEM public key")
    key_parser.add_argument("pem_file", type=str, help="Path to PEM public key file")
    _add_common_args(key_parser)

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=["auto", "quantum", "classical"],
        default="auto",
        help="Order-finding mode (default: auto)",
    )
    parser.add_argument("--max-qubits", type=int, default=27, help="Max qubits for quantum simulation (default: 27)")
    parser.add_argument("--attempts", type=int, default=30, help="Max Shor attempts (default: 30)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    parser.add_argument("--force", action="store_true", help="Force quantum mode even if qubit count is high")
    parser.add_argument("--verbose", action="store_true", help="Show circuit details and measurements")
    parser.add_argument("--quiet", action="store_true", help="Only output the factors")


def _run_factor(n: int, args) -> int:
    """Run the factoring algorithm on n. Returns exit code."""
    verbose_cb = print_info if args.verbose else None

    mode = _resolve_mode(n, args.mode, args.max_qubits, args.force)

    if not args.quiet:
        needed = qubits_needed(n)
        print_info(f"Factoring {n} ({n.bit_length()}-bit, {needed} qubits needed)")
        print_info(f"Mode: {mode}")

    if mode == "quantum":
        order_finder = QuantumOrderFinder(verbose_callback=verbose_cb)
    else:
        if n.bit_length() > 60 and not args.force:
            print_error(
                f"N={n} is {n.bit_length()}-bit. Classical brute-force order finding "
                f"is infeasible for numbers this large. A real quantum computer would "
                f"be needed. Use --force to try anyway."
            )
            return 1
        order_finder = ClassicalOrderFinderAdapter()

    try:
        result = factor(n, order_finder, max_attempts=args.attempts, verbose_callback=verbose_cb)
    except ValueError as exc:
        print_error(str(exc))
        return 1

    print_result(result.n, result.factors, result.method, quiet=args.quiet)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "factor":
        return _run_factor(args.n, args)

    elif args.command == "factor-key":
        from shorkin.rsa import extract_modulus

        try:
            n = extract_modulus(args.pem_file)
        except (FileNotFoundError, ValueError) as exc:
            print_error(str(exc))
            return 1

        if not args.quiet:
            print_info(f"RSA modulus: {n} ({n.bit_length()}-bit)")

        return _run_factor(n, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
