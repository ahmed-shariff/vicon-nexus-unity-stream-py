#!/usr/bin/env python

"""Main script."""

import log

from flask import Flask
from flask_restful import Resource, Api

try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    log.e("Make sure vicon DataStreamSDK is installed: Follow the instructions in https://www.vicon.com/software/datastream-sdk/\n")
    raise


def get_client(connection=None):
    if connection is None:
        connection = 'localhost:801'
    client = ViconDataStream.Client()

    log.i('Connecting...')
    while not client.IsConnected():
        client.Connect(connection)
    log.i('Connected to vicon data stream')
    return client
    

def _init_api(connection=None):
    client = get_client(connection)
    app = Flask("vicon-ds")
    api = Api(app)

    class ViconMarkerStream(Resource):
        def get(self):
            if client.IsConnected() and client.GetFrame():
                return {"data": {"markers": 10}}
            
    api.add_resource(ViconMarkerStream, '/')
    app.run()
    
            
def main(connection=None):
    client = get_client(connection)
    try:
        while client.IsConnected():
            if client.GetFrame():
                # send data
                pass

    except ViconDataStream.DataStreamException as e:
        log.e( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
