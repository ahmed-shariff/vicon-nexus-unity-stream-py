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
    client.EnableSegmentData()
    return client
    

def _init_api(connection=None):
    client = get_client(connection)
    app = Flask("vicon-ds")
    api = Api(app)

    class ViconMarkerStream(Resource):
        def get(self):
            if client.IsConnected() and client.GetFrame():
                return {"data": get_data(client, 'test')}
            
    api.add_resource(ViconMarkerStream, '/')
    app.run()


def get_data(client, subject_name):
    data = {}
    # print(*[n for n in client.__dir__() if "G" in n], sep="\n")
    for segment in client.GetSegmentNames(subject_name):
        segment_data = {}
        translation, status = client.GetSegmentGlobalTranslation(subject_name, segment)
        segment_data['translation'] = translation
        segment_data['translation_status'] = status
        rotation, status = client.GetSegmentGlobalRotationMatrix(subject_name, segment)
        segment_data['rotation'] = rotation
        segment_data['rotation_status'] = status
        data[segment] = segment_data
    return data


def main(connection=None):
    client = get_client(connection)
    try:
        if client.IsConnected():
            if client.GetFrame():
                print(get_data(client, 'test'))

    except ViconDataStream.DataStreamException as e:
        log.e( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
