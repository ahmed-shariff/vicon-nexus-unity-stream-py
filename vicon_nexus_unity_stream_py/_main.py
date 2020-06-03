#!/usr/bin/env python

"""Main script."""

import log
try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    log.e("Make sure vicon DataStreamSDK is not installed\n")
    raise

def main():
    client = ViconDataStream.Client()

    log.i( 'Connecting...' )
    while not client.IsConnected():
        client.Connect( 'localhost:801' )
    log.i( 'Connected to vicon data stream' )

    try:
        while client.IsConnected():
            if client.GetFrame():
                # send data
                pass

    except ViconDataStream.DataStreamException as e:
        log.e( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
