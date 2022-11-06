#!/usr/bin/env python

"""Main script."""

import json
import msgpack
import pandas as pd
from pathlib import Path
from datetime import datetime

from flask import Flask, send_file, make_response
from flask_restful import Resource, Api
from loguru import logger

from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput, VoltageRatioSensorType

try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    logger.error("Make sure vicon DataStreamSDK is installed: Follow the instructions in https://www.vicon.com/software/datastream-sdk/\n")
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

    logger.info('Connecting...')
    while not client.IsConnected():
        client.Connect(connection)
    logger.info('Connected to vicon data stream')
    client.EnableSegmentData()
    client.EnableMarkerData()
##    client.SetAxisMapping(ViconDataStream.Client.AxisMapping.EForward,
##                          ViconDataStream.Client.AxisMapping.EUp,
##                          ViconDataStream.Client.AxisMapping.ELeft)
    logger.info(client.GetAxisMapping())
    return client

def setup_phidget():
    logger.info("Setting up sensor")
    voltageRatioInput0 = VoltageRatioInput()
    voltageRatioInput0.setIsHubPortDevice(True)
    voltageRatioInput0.setHubPort(0)
    voltageRatioInput0.setOnSensorChangeHandler(onSensorChange)
    voltageRatioInput0.openWaitForAttachment(5000)    
    voltageRatioInput0.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_1120)
    voltageRatioInput0.setDataInterval(1)
    logger.info("sensor ready")
    return voltageRatioInput0


def process_return_value(ret_val, use_json=False):
    if use_json:
        return ret_val
    else:
        if isinstance(ret_val, tuple):
            response = make_response(msgpack.packb(ret_val[0]), ret_val[1])
        else:
            response = make_response(msgpack.packb(ret_val))
        response.headers['content-type'] = 'application/msgpack'
        return response


def _init_api(connection=None, host="127.0.0.1", port="5000", use_json=False):
    try:
        client = get_client(connection)
    except Exception as e:
        logger.error("Failed to connect to client")
        logger.error(e.message)
        client = None
    app = Flask("vicon-ds")
    api = Api(app)
    try:
        sensor = setup_phidget()
    except Exception as e:
        logger.error("Failed to connect to sensor")
        logger.error(e)
        sensor = None

    class ViconMarkerStream(Resource):
        def get(self, data_type, subject_name):
            ret_val = self._get(data_type, subject_name)
            return process_return_value(ret_val, use_json)

        def _get(self, data_type, subject_name):
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

def _init_api_static(connection=None, host="127.0.0.1", port="5000", input_file=None, use_json=False):
    app = Flask("vicon-ds")
    api = Api(app)
    # try:
    #     sensor = setup_phidget()
    # except Exception as e:
    #     logger.error("Failed to connect to sensor")
    #     logger.error(e.message)
    #     sensor = None

    if input_file is None or len(input_file) == 0:
        logger.error("`input_file` cannot be empty")
        return

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
        def _set_index(self, idx):
            global IDX
            if idx >= LINES.index.max():
                IDX = 0
            elif idx < 0:
                IDX = int(LINES.index.max())
            else:
                IDX = idx

        def get(self, process=None, param=None):
            ret_val = self._get(process, param)
            return process_return_value(ret_val, use_json=True)

        def _get(self, process=None, param=None):
            global IDX, PLAY_MODE, PLAY_INDEX, PLAY_TS
            if process is None or process == "index":
                return send_file(Path(__file__).parent / "static" / "index.html")
            elif process == "n":
                self._set_index(IDX + 1)
                return IDX
            elif process == "p":
                self._set_index(IDX - 1)
                return IDX
            elif process == "s":
                if param is None:
                    return "param cannot be empty. Use: /offline/s/<frame-number>", 404
                try:
                    self._set_index(int(param))
                    return IDX
                except:
                    return "param should be a number. Use: /offline/s/<frame-number>", 404
            elif process == "t":
                PLAY_MODE = not PLAY_MODE
                if PLAY_MODE:
                    PLAY_INDEX = LINES.iloc[IDX, 0]
                    PLAY_TS = datetime.now().timestamp()
                else:
                    self._set_index(int(LINES[LINES.iloc[:, 0] == PLAY_INDEX].index[0]))
                return PLAY_MODE
            return "Process not recognized. Available processes: offline/n  = Next, offline/p = Previous, offline/s/<frame-number> = jump to frame-number, offline/t = toggle play mode", 404

    class ViconMarkerStream(Resource):
        def get(self, data_type, subject_name):
            ret_val = self._get(data_type, subject_name)
            return process_return_value(ret_val, use_json)

        def _get(self, data_type, subject_name):
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
    print(f"Go to `http://{host}:{port}/offline/index` to access the web UI")
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
        logger.info(f"{len(sensor_triggered)}, {data['sensorTriggered']}")
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
        logger.error( f'Error: {e}' )


if __name__ == '__main__':  # pragma: no cover
    main()
