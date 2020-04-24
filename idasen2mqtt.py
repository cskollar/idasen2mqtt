import threading
import time
import sys
import struct
from bluepy.btle import Peripheral, ADDR_TYPE_RANDOM
import paho.mqtt.client as mqtt
import json

#settings

desk_address = "cb:6d:34:b2:52:d3"
mqtt_server = "10.20.20.3"
mqtt_port = 1883
desk_service_uuid = "99fa0020-338a-1024-8a49-009c0215f78a"
desk_handler = 0x0010
payload_up = "4700"
payload_down = "4600"
payload_stop = "ff00"

#init BLE

p = Peripheral(desk_address, ADDR_TYPE_RANDOM)

#move&control the desk

def position():
    current_position = struct.unpack('<H', p.readCharacteristic(26)[0:2])[0]
    return current_position

def moveDesk(to_position, payload):
    p.writeCharacteristic(0x0010, bytes.fromhex(payload_stop))
    while True:
        #based on many tests abs() is the fastest/precise way to check the position while moving the desk (to avoid overrun)
        #it stops the desk when the current and the desired position differ by 1% (height value 65)
        if abs(to_position-position()) >= 65:
            p.writeCharacteristic(desk_handler, bytes.fromhex(payload))
            time.sleep(0.1)
        else:
            p.writeCharacteristic(desk_handler, bytes.fromhex(payload_stop))
            return None

def setDesk(name, to_position, client):
    current_position = position()
    #do nothing when diff < 1%
    if abs(to_position-current_position) <= 65:
        raise SystemExit
    elif current_position < to_position:
        client.publish(topic="desk/state", payload="moving up", qos=1, retain=False)
        moveDesk(to_position, payload_up)
        client.publish(topic="desk/state", payload="stop", qos=1, retain=False)
        client.publish(topic="desk/height", payload=round((position()/65)), qos=1, retain=False)
    elif current_position > to_position:
        client.publish(topic="desk/state", payload="moving down", qos=1, retain=False)
        moveDesk(to_position, payload_down)
        client.publish(topic="desk/state", payload="stop", qos=1, retain=False)
        client.publish(topic="desk/height", payload=round((position()/65)), qos=1, retain=False)
    #print some debug info to stdout
    time.sleep(2)
    current =  position()
    to_position_percentagle = (to_position / 65)
    print (f"actual: {current} ({(current / 65)}%)")
    print (f"expected: {to_position} ({to_position_percentagle}%)")
    print ("diff: ", abs(to_position-current))
    print (f"accuracy: {round((abs(to_position-current) / 65),2)}%")
    raise SystemExit

# MQTT and main loop

def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected With Result Code: {}".format(rc))
    client.publish(topic="desk/online", payload="true", qos=1, retain=False)
    return None

def on_mqtt_disconnect(client, userdata, rc):
    print("Client Got Disconnected")
    client.publish(topic="desk/online", payload="false", qos=1, retain=False)
    return None

def on_mqtt_command(client, userdata, message):
    if message.payload.decode() == "announce":
        client.publish(topic="desk/height", payload=round((position()/65)), qos=1, retain=False)
        client.publish(topic="desk/online", payload="true", qos=1, retain=False)
    return None

def on_mqtt_set(client, userdata, message):
    try:
        to_position = (int(message.payload.decode()) * 65)
        if 0 <= to_position <= 6500:
            #start separate thread for move the desk (it's necessary to avoid breaking the mqtt network loop)
            y = threading.Thread(target=setDesk, args=("set", to_position, client))
            y.start()
        return None
    except:
        print ("error")
        return None

def report_height(name,client):
    while True:
        client.publish(topic="desk/height", payload=round((position()/65)), qos=1, retain=False)
        print("status published")
        time.sleep(60)

def main():
    #setup mqtt client
    client = mqtt.Client()
    client.connect(mqtt_server, mqtt_port)
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.subscribe("desk/command", qos=1)
    client.subscribe("desk/set", qos=1)
    client.message_callback_add("desk/command", on_mqtt_command)
    client.message_callback_add("desk/set", on_mqtt_set)
    #start separate thread for periodic height reporting (it's necessary to avoid breaking the mqtt network loop)
    x = threading.Thread(target=report_height, args=("report",client))
    x.start()
    #start mqtt network loop
    client.loop_forever()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        p.disconnect()
