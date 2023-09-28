import logging
import os

import azure.functions as func
from azure.core.exceptions import HttpResponseError
from azure.digitaltwins.core import DigitalTwinsClient
from azure.identity import DefaultAzureCredential
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Twin, TwinProperties

app = func.FunctionApp()


@app.event_grid_trigger(arg_name="azeventgrid")
def twin_iothub_update(azeventgrid: func.EventGridEvent):
    """Function to update IoTHub Device Twin desired properties

    Parameters
    ----------
    azeventgrid : func.EventGridEvent
        event grid topic to consume from, initialise from iothub
    """
    logging.info("Python EventGrid trigger processed an event")

    CONNECTION_STRING = "HostName=ESP32Experiment.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=f2JNzQ4e0ul0x3f0aUcfcQ56wQnSxAg5KfRlswhuP3k="

    # converts data field of device telemetry event to dictionary
    # ref : https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-event-grid#device-telemetry-schema
    data = azeventgrid.get_json()
    logging.info(data["data"]["patch"])

    logging.info(azeventgrid.subject)

    desired_properties_patch = data["data"]["patch"]
    desired_properties = {}

    for property_patch in desired_properties_patch:
        twin_property = property_patch["path"].split("/")[1]
        twin_property_value = property_patch["value"]

    desired_properties[twin_property] = twin_property_value

    if azeventgrid.subject == "ModbusDevice":
        device_id = "IIoT_Modbus"
    else:
        device_id = azeventgrid.subject
    # device_id = device_lut[azeventgrid.subject]

    # Create IoTHubRegistryManager
    registry_manager = IoTHubRegistryManager(CONNECTION_STRING)

    twin = registry_manager.get_twin(device_id)
    twin_patch = Twin(properties=TwinProperties(desired=desired_properties))
    registry_manager.update_twin(device_id, twin_patch, twin.etag)




@app.event_grid_trigger(arg_name="azeventgrid")
def modbus_to_adt(azeventgrid: func.EventGridEvent):
    """Function to update ADT using Azure Event Grid Event

    Parameters
    ----------
    azeventgrid : func.EventGridEvent
        event grid topic to consume from, initialise from iothub
    """
    logging.info("Python EventGrid trigger processed an event")

    # converts data field of device telemetry event to dictionary
    # ref : https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-event-grid#device-telemetry-schema
    data = azeventgrid.get_json()
    logging.info(data)

    # url = os.environ.get("ADT_MODBUS_HOSTNAME")
    # url = "https://IIoT-Modbus.api.eus.digitaltwins.azure.net"
    url = "https://iot-digital-twin-poc.api.wcus.digitaltwins.azure.net"

    # Create ADT client
    credential = DefaultAzureCredential()
    service_client = DigitalTwinsClient(url, credential)

    # Get device ID from Azure Event Grid Event
    deviceId = data["systemProperties"]["iothub-connection-device-id"]
    if deviceId == "IIoT_Modbus":
        # get the node name
        node_name = data["body"][0]["node_name"]
        if node_name == "Modbus_TCP_Device_1":
            group_name = data["body"][0]["group_name"]
            # Get the group name and update the DT based on twin id
            if group_name == "Ambient_Sensor":
                telemetry = data["body"][0]["values"]
                logging.info(telemetry)
                digita_twin_id = "Ambient_Sensor"
                patch = [
                    {
                        "op": "replace",
                        "path": "/Temperature",
                        "value": telemetry["Temperature"],
                    },
                    {
                        "op": "replace",
                        "path": "/Humidity",
                        "value": telemetry["Humidity"],
                    },
                    {
                        "op": "replace",
                        "path": "/Air_Quality",
                        "value": telemetry["Air_Quality"],
                    },
                ]
                logging.info(patch)
                # service_client.publish_telemetry(digita_twin_id, telemetry)
                try:
                    service_client.update_digital_twin(digita_twin_id, patch)
                except HttpResponseError:
                    for patch_block in patch:
                        patch_block["op"] = "add"
                    service_client.update_digital_twin(digita_twin_id, patch)

            if group_name == "Machine_1":
                telemetry = data["body"][0]["values"]
                logging.info(telemetry)
                digita_twin_id = "Machine_1"
                patch = [
                    {
                        "op": "replace",
                        "path": "/Avg_Current",
                        "value": telemetry["Avg_Current"],
                    },
                    {
                        "op": "replace",
                        "path": "/Winding_Temperature",
                        "value": telemetry["Winding_Temperature"],
                    },
                ]
                # service_client.publish_telemetry(digita_twin_id, telemetry)
                try:
                    service_client.update_digital_twin(digita_twin_id, patch)
                except HttpResponseError:
                    for patch_block in patch:
                        patch_block["op"] = "add"
                    service_client.update_digital_twin(digita_twin_id, patch)
                logging.info(patch)
