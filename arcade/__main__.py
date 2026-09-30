"""`python -m arcade`: the wall arcade. The guard matters: the colorlight driver's sender is a spawned child,
which imports the main module again."""
import sys

from arcade.main import main

if __name__ == "__main__":
    sys.exit(main())
