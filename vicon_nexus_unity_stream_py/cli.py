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
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
def server(connection, host, port):
    _init_api(connection, host, port)


_main.add_command(test)
_main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
