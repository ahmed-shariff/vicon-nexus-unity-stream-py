from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput, VoltageRatioSensorType
import time

def onSensorChange(self, sensorValue, sensorUnit):
	print("SensorValue: " + str(sensorValue))
	print("SensorUnit: " + str(sensorUnit.symbol))
	print("----------")

def main():
	voltageRatioInput0 = VoltageRatioInput()

	voltageRatioInput0.setIsHubPortDevice(True)
	voltageRatioInput0.setHubPort(0)

	voltageRatioInput0.setOnSensorChangeHandler(onSensorChange)

	voltageRatioInput0.openWaitForAttachment(5000)

	voltageRatioInput0.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_1120)

	try:
		input("Press Enter to Stop\n")
	except (Exception, KeyboardInterrupt):
		pass

	voltageRatioInput0.close()

main()
