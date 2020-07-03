from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
import time

def onVoltageRatioChange(self, voltageRatio):
    if voltageRatio > 0.02:
        print("VoltageRatio: " + str(voltageRatio))

def main():
    voltageRatioInput0 = VoltageRatioInput()
    
    voltageRatioInput0.setIsHubPortDevice(True)
    voltageRatioInput0.setHubPort(0)

    print(*[x for x in voltageRatioInput0.__dir__() if "DataInterval" in x], sep="\n")
    
    voltageRatioInput0.setOnVoltageRatioChangeHandler(onVoltageRatioChange)
    
    voltageRatioInput0.openWaitForAttachment(5000)

    print(voltageRatioInput0.getMinDataInterval(), voltageRatioInput0.getMaxDataInterval())
    voltageRatioInput0.setDataInterval(100)
    voltageRatioInput0.setSensorValueChangeTrigger(0.01)
    try:
        input("Press Enter to Stop\n")
    except (Exception, KeyboardInterrupt):
        pass

    voltageRatioInput0.close()

if __name__ == "__main__":
    main()
