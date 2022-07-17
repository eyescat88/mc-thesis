import sys
import argparse

RC = 0


def argbaseparser(options=None):
    """Base Argument Parser."""
    parser = argparse.ArgumentParser(add_help=False, conflict_handler="resolve")
    parser.add_argument(
        "-x", "--exec", type=str, help="command to dispatch", default="_"
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="increase output verbosity"
    )
    return parser


def argparser(options=None):
    """create a inherited Argument Parser."""
    parent = argbaseparser(options=options)
    parser = argparse.ArgumentParser(parents=[parent], conflict_handler="resolve")
    return parser


def parse_args(argv=None):
    """Process command line arguments."""
    if not argv:
        argv = sys.argv[1:]

    parser = argparser()
    args, unknown = parser.parse_known_args(argv)
    return args


def exec(args, argv=None):
    """Dispatch execution to target entry point."""

    entry = args.exec
    if entry == "_":
        entry = "main"

    if entry == "main":
        import dve.scripts.runner as runner

        RC = runner.main(argv)
    else:
        raise ValueError(f"invalid command: {entry}!")
    return RC


def main(argv=None):
    """Process command line arguments."""
    args = parse_args(argv)
    RC = exec(args, argv=argv)
    return RC


if __name__ == "__main__":
    main()
