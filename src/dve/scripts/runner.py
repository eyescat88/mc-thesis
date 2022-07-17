import sys
import logging

import dve.cli as cli

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


def argparser(options=None):
    """Base Argument Parser."""
    parser = cli.argparser(options)

    parser.add_argument("-c", "--cmd", type=str, help="script to execute", default="_")
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

    cmd = args.cmd
    if cmd == "_":
        cmd = "auto"

    if cmd == "auto":
        import dve.scripts.auto as script

        RC = script.main(argv)
    elif cmd == "test":
        print("#<test>:" + str(args))
        RC = 0
    else:
        raise ValueError(f"invalid command: {cmd}!")
    return RC


def main(argv=None):
    """Process command line arguments."""
    print(__name__ + "main:" + str(argv))
    log.info(">> ### " + __name__ + ".main(argv=" + str(argv) + ")")
    args = parse_args(argv)
    RC = exec(args, argv)
    log.info("<< ###" + __name__ + ".main => (rc=" + str(RC) + ")")
    return RC


if __name__ == "__main__":
    main(sys.argv[1:])
