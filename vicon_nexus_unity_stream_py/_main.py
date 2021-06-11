#!/usr/bin/env python

"""Main script."""

import log
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from flask import Flask, send_file
from flask_restful import Resource, Api
from loguru import logger

from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput, VoltageRatioSensorType

try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    log.e("Make sure vicon DataStreamSDK is installed: Follow the instructions in https://www.vicon.com/software/datastream-sdk/\n")
    #raise

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
    logger.info(client.GetAxisMapping())
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
        log.e(e)
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


LINES = []
IDX = 0
PLAY_MODE = False
PLAY_INDEX = None
PLAY_TS = None

def _init_api_static(connection=None, host="127.0.0.1", port="5000", input_file=None):
    app = Flask("vicon-ds")
    api = Api(app)
    # try:
    #     sensor = setup_phidget()
    # except Exception as e:
    #     log.e("Failed to connect to sensor")
    #     log.e(e.message)
    #     sensor = None

    _lines = []
    with open(input_file) as f:
        for l in f.readlines():
            if len(l.strip()) == 0:
                continue
            _lines.append(l.rstrip().split(",", maxsplit=1))

    global LINES
    LINES = pd.DataFrame(_lines)
    LINES[1] = LINES[1].apply(lambda x: x if len(x) > 0 else None)
    LINES = LINES.dropna()
    LINES[0] = pd.to_numeric(LINES[0])

    # TODO: better validation?
    class ViconMarkerStreamProcess(Resource):
        def get(self, process=None, param=None):
            global IDX, PLAY_MODE, PLAY_INDEX, PLAY_TS
            if process is None or process == "index":
                return send_file(Path(__file__).parent / "static" / "index.html")
            elif process == "n":
                IDX += 1
                return IDX
            elif process == "p":
                IDX -= 1
                return IDX
            elif process == "s":
                if param is None:
                    return "param cannot be empty. Use: /offline/s/<frame-number>", 404
                try:
                    IDX = int(param)
                    return IDX
                except:
                    return "param should be a number. Use: /offline/s/<frame-number>", 404
            elif process == "t":
                PLAY_MODE = not PLAY_MODE
                if PLAY_MODE:
                    PLAY_INDEX = LINES.iloc[IDX, 0]
                    PLAY_TS = datetime.now().timestamp()
                else:
                    IDX = int(LINES[LINES.iloc[:, 0] == PLAY_INDEX].index[0])
                return PLAY_MODE
            return "Process not recognized. Available processes: offline/n  = Next, offline/p = Previous, offline/s/<frame-number> = jump to frame-number, offline/t = toggle play mode", 404

    class ViconMarkerStream(Resource):
        def get(self, data_type, subject_name):
            global PLAY_INDEX, PLAY_TS
            if subject_name == 'test':
                if PLAY_MODE:
                    index = LINES.iloc[:, 0]
                    diff = (index - PLAY_INDEX)
                    min_val = index[diff > 0].min()
                    ts = datetime.now().timestamp()
                    if ts - PLAY_TS >= 0:
                        PLAY_INDEX = min_val
                        PLAY_TS = ts
                    if min_val == index.max():
                        PLAY_INDEX = index.min()
                        PLAY_TS = datetime.now().timestamp()
                    return json.loads(LINES[index == PLAY_INDEX].iloc[0, 1])
                else:
                    return json.loads(LINES.iloc[IDX, 1])
            return "Only works for subject `test`", 404

    api.add_resource(ViconMarkerStream, '/<string:data_type>/<string:subject_name>')
    api.add_resource(ViconMarkerStreamProcess, '/offline/<string:process>', '/offline/<string:process>/<string:param>', '/offline')
    app.run(host=host, port=int(port))
            

def get_data(client, data_type, subject_name):
    global sensor_triggered, previous_sensor_triggered
    data = {}
    # logger.info(*[n for n in client.__dir__() if "G" in n], sep="\n")
    # slogger.info(client.GetSegmentNames(subject_name))
    if data_type == "marker":
        marker_segment_data = {}
        marker_data = {}
        for marker, segment in client.GetMarkerNames(subject_name):
            try:
                marker_segment_data[segment].append(marker)
            except KeyError:
                marker_segment_data[segment] = [marker]
            marker_data[marker] = client.GetMarkerGlobalTranslation(subject_name, marker)[0]
            # logger.info(client.GetMarkerGlobalTranslation(subject_name, marker))
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
        logger.info(len(sensor_triggered), data['sensorTriggered'])
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
                logger.info(get_data(client, 'test'))

    except ViconDataStream.DataStreamException as e:
        log.e( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
