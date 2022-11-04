"""CLI."""

import click

from ._main import main, _init_api, _init_api_static

@click.group()
def _main():
    pass


@click.command()
@click.option("-c", "--connection", default='localhost:801')
def test(connection):
    """Test if connection is working"""
    main(connection)


@click.command()
@click.option("-c", "--connection", default='localhost:801')
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
def server(connection, host, port):
    """Connects to the vicon and streams the data out through host:port"""
    _init_api(connection, host, port)


@click.command()
@click.option("-c", "--connection", default='localhost:801')
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
@click.option("-f", "--file", default=None)
def stream(connection, host, port, file):
    """
    Instead of connecting to vicon, streams data from a csv file. The format of the file is
    the same as the one recorded by https://github.com/ahmed-shariff/vicon-nexus-unity-stream.
    """
    _init_api_static(connection, host, port, file)


_main.add_command(test)
_main.add_command(server)
_main.add_command(stream)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
