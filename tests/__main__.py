import argparse
import sys
import unittest
from pathlib import Path


def build_parser():
    """Create the CLI parser for the cross-platform test runner."""
    parser = argparse.ArgumentParser(
        description='Run the project unittest suite in a cross-platform way.'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Show individual test names and statuses.'
    )
    parser.add_argument(
        '-p',
        '--pattern',
        default='test*.py',
        help='Glob pattern used to discover test files.'
    )
    parser.add_argument(
        '-s',
        '--start-directory',
        default=str(Path(__file__).resolve().parent),
        help='Directory where test discovery starts.'
    )
    parser.add_argument(
        '-t',
        '--top-level-directory',
        default=str(Path(__file__).resolve().parent.parent),
        help='Top-level project directory used for imports during discovery.'
    )
    return parser


def main(argv=None):
    """Discover and run the unittest suite."""
    parser = build_parser()
    args = parser.parse_args(argv)

    suite = unittest.defaultTestLoader.discover(
        start_dir=args.start_directory,
        pattern=args.pattern,
        top_level_dir=args.top_level_directory
    )
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

