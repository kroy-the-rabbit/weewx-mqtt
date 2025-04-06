# File: install.py

from weecfg.extension import ExtensionInstaller

def loader():
    """Extension loader."""
    return MQTTDriverInstaller()

class MQTTDriverInstaller(ExtensionInstaller):
    def __init__(self):
        super(MQTTDriverInstaller, self).__init__(
            version="0.3",
            name="MQTTDriver",
            description="WeeWX driver that subscribes directly to MQTT messages.",
            author="kroy",
            author_email="kroy@kroy.io",
            files=[('bin/user', ['bin/user/mqtt_driver.py'])],
            config={
                'Station': {
                    'station_type': 'MQTTDriver'
                },
                'MQTTDriver': {
                }
            },
            install_requires=['paho-mqtt']
        )

