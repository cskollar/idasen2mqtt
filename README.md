# idasen2mqtt

This is a working proof on concept code for control IKEA IDÃSEN standing desk through mqtt. Payloads were reverse engineered from BLE traffic of IKEA/Linak Desk Control application.

## mqtt commands

After idasen2mqtt.py started you can send position commands (in %) to desk/set topic (e.g. from Home Assistant).

Example for move to 22% of height with Mosquitto mqtt client:

    $ mosquitto_pub -h mqtt.broker.host -t "desk/set" -m "22"

## mqtt topics

desk/set - height command topic

desk/height - current position in % (published in every minute)

desk/state - current state ("stop", "moving up" or "moving down")

desk/command - other command topic (only the command "announce" implemented at this time)



