# weewx-mqtt

This is a simple adapter to allow weewx to ingest mqtt.

I wrote this because of the ease of integrating random ESP32 devices.


# Example packet:

```
❯ mqttcli sub --host="mqtt.lan.kroy.io" -t "rtl_433/analog/events"
{"time":"2025-04-06 04:43:04","model":"ESP32s","sequence_num":0,"temperature_C":13.77,"temperature_F":56.79,"id":"66838BA28DCC","pressure_hPa":982.12,"pressure_inHg":29.00191,"altitude_m":262.4896,"altitude_ft":861.1863}

```

# Example config

`mqtt.conf`

```

[MQTTDriver]
    host = mqtt.lan.kroy.io
    topic = rtl_433/analog/events
    poll_interval = 5
    driver = user.mqtt_driver
    usUnits = weewx.METRICWX  # Incoming data is in metric units



    [ModelMappings]

    [[ESP32s]]
        # Target ESP32s with id 66838BA28DCC
        pressure = pressure_hPa.ESP32s.66838BA28DCC   # Pressure in hPa
        altitude = altitude_m.ESP32s.66838BA28DCC  # Altitude in m



```

# Install

`weectl extension install weewx-mqtt-0.5.zip`

