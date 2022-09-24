def find_rest_device_by_thing_name(rest_devices, thing_name):
    for rest_device in rest_devices:
        if rest_device.thing_name == thing_name:
            return rest_device
