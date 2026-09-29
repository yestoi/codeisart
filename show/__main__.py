"""`python -m show`: the show daemon (deploy/show.service runs it)."""
import sys

from show.main import main

if __name__ == "__main__":
    sys.exit(main())
