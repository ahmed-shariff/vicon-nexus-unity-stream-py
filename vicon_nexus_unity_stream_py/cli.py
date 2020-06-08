"""CLI."""

import click
import log

from ._main import main, _init_api

@click.group()
def _main():
    log.init()


@click.command()
@click.option("-c", "--connection", default='localhost:801')
def test(connection):
    main(connection)


@click.command()
@click.option("-c", "--connection", default='localhost:801')
def server(connection):
    _init_api(connection)


_main.add_command(test)
_main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
