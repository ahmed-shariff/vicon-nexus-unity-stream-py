#!/usr/bin/env python

"""Main script."""

import log

from flask import Flask
from flask_restful import Resource, Api

from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput, VoltageRatioSensorType

try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    log.e("Make sure vicon DataStreamSDK is installed: Follow the instructions in https://www.vicon.com/software/datastream-sdk/\n")
    raise

sensor_triggered = []
previous_sensor_triggered = False

def onSensorChange(self, sensorValue, sensorUnit):
    if sensorValue > 0.03:
        global sensor_triggered
        sensor_triggered.append(1)

def get_client(connection=None):
    if connection is None:
        connection = 'localhost:801'
    client = ViconDataStream.Client()

    log.i('Connecting...')
    while not client.IsConnected():
        client.Connect(connection)
    log.i('Connected to vicon data stream')
    client.EnableSegmentData()
    client.EnableMarkerData()
##    client.SetAxisMapping(ViconDataStream.Client.AxisMapping.EForward,
##                          ViconDataStream.Client.AxisMapping.EUp,
##                          ViconDataStream.Client.AxisMapping.ELeft)
    print(client.GetAxisMapping())
    return client

def setup_phidget():
    log.i("Setting up sensor")
    voltageRatioInput0 = VoltageRatioInput()
    voltageRatioInput0.setIsHubPortDevice(True)
    voltageRatioInput0.setHubPort(0)
    voltageRatioInput0.setOnSensorChangeHandler(onSensorChange)
    voltageRatioInput0.openWaitForAttachment(5000)    
    voltageRatioInput0.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_1120)
    voltageRatioInput0.setDataInterval(1)
    log.i("sensor ready")
    return voltageRatioInput0


def _init_api(connection=None, host="127.0.0.1", port="5000"):
    try:
        client = get_client(connection)
    except Exception as e:
        log.e("Failed to connect to client")
        log.e(e.message)
        client = None
    app = Flask("vicon-ds")
    api = Api(app)
    try:
        sensor = setup_phidget()
    except Exception as e:
        log.e("Failed to connect to sensor")
        log.e(e.message)
        sensor = None

    class ViconMarkerStream(Resource):
        def get(self, data_type, subject_name):
            if client is not None and client.IsConnected() and client.GetFrame():
                return get_data(client, data_type, subject_name)
            return "restart:  client didn't connect", 404

    api.add_resource(ViconMarkerStream, '/<string:data_type>/<string:subject_name>')
    try:
        app.run(host=host, port=int(port))
    finally:
        if sensor is not None:
            sensor.close()


def get_data(client, data_type, subject_name):
    global sensor_triggered, previous_sensor_triggered
    data = {}
    # print(*[n for n in client.__dir__() if "G" in n], sep="\n")
    # sprint(client.GetSegmentNames(subject_name))
    if data_type == "marker":
        marker_segment_data = {}
        marker_data = {}
        for marker, segment in client.GetMarkerNames(subject_name):
            try:
                marker_segment_data[segment].append(marker)
            except KeyError:
                marker_segment_data[segment] = [marker]
            marker_data[marker] = client.GetMarkerGlobalTranslation(subject_name, marker)[0]
            # print(client.GetMarkerGlobalTranslation(subject_name, marker))
        data['data'] = marker_data
        data['hierachy'] = marker_segment_data
        
        if len(sensor_triggered) > 1:
            data['sensorTriggered'] = True
            previous_sensor_triggered = True
        elif previous_sensor_triggered:
            data['sensorTriggered'] = True
            previous_sensor_triggered = False
        else:
            data['sensorTriggered'] = False
            previous_sensor_triggered = False
        print(len(sensor_triggered), data['sensorTriggered'])
        sensor_triggered = []
        
    elif data_type == "segment":
        segment_data = {}
        for segment in client.GetSegmentNames(subject_name):
            translation, status = client.GetSegmentGlobalTranslation(subject_name, segment)
            rotation, status = client.GetSegmentGlobalRotationQuaternion(subject_name, segment)
            segment_data[segment] = translation + rotation
        data['data'] = segment_data
            
    return data


def main(connection=None):
    client = get_client(connection)
    try:
        while client.IsConnected():
            if client.GetFrame():
                print(get_data(client, 'test'))

    except ViconDataStream.DataStreamException as e:
        log.e( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
