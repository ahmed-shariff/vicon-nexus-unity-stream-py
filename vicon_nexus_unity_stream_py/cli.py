"""CLI."""

import click
import log

from ._main import main

@click.command()
def _main():
    log.init()
    main()


if __name__ == '__main__':  # pragma: no cover
    _main()
