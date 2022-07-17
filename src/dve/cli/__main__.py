import sys
import argparse

import dve.cli


def main(argv=None):
    """Process command line arguments."""
    return dve.cli.main(argv=argv)


if __name__ == "__main__":
    main(sys.argv[1:])
