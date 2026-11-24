"""Offline smoke tests; can run on Windows without installing Home Assistant.

Run: python -m unittest discover -s tests -v
Requires: httpx cryptography
"""

from __future__ import annotations

import base64
import importlib
import json
import pathlib
import sys
import types
import unittest

COMPONENT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components"
    / "broadlink_cloud"
)
# Bypass package __init__.py so Home Assistant needn't be installed on Windows.
PKG_NAME = "_bl_test_protocol"
package = types.ModuleType(PKG_NAME)
package.__path__ = [str(COMPONENT_PATH)]
sys.modules[PKG_NAME] = package
api = importlib.import_module(f"{PKG_NAME}.api")


def demo_hub():
    creds = {"terminalid": 101, "aeskey": "demo-aes-key"}
    return {
        "endpointId": "demo-hub",
        "productId": "product",
        "mac": "00:00:00:00:00:01",
        "devicetypeFlag": 1,
        "friendlyName": "Woonkamer",
        "cookie": base64.b64encode(json.dumps(creds).encode()).decode(),
    }


class Response:
    def __init__(self, obj: dict):
        self.obj = obj

    def raise_for_status(self):
        return None

    def json(self):
        return self.obj


class FakeHttpClient:
    def __init__(self):
        self.requests = []
        self.physical = demo_hub()
        self.remote = {"endpointId": "demo-remote", "friendlyName": "Keukenlamp"}

    def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        if url.endswith("/account/login"):
            return Response({"error": 0, "userid": "account-id", "loginsession": "session"})
        if url.endswith("/getfamilylist"):
            return Response({"status": 0, "data": {"familyList": [{"familyid": "home", "name": "My home"}]}})
        if url.endswith("/dev/query?action=select"):
            return Response({"status": 0, "data": {"endpoints": [self.physical, self.remote]}})
        if url.endswith("/ircode/query"):
            if kwargs['json']['endpointId'] == "demo-hub":
                return Response({"status": 0, "data": {"endpointId": "not-demo-hub"}})
            return Response({"status": 0, "data": {
                "endpointId": "demo-remote", "irData": [
                    {"name": "Power", "codeList": [{"code": "26005000"}]},
                    {"name": "Macro", "codeList": [{"code": "01"}, {"code": "02"}]},
                ]
            }})
        if url.endswith("/device/control/v2/sdkcontrol"):
            req = kwargs['json']
            head = req['directive']['header']
            endpoint = req['directive']['endpoint']
            return Response({"event": {
                "header": {
                    "namespace": "DNA.TransmissionControl",
                    "name": "Response",
                    "interfaceVersion": "2",
                    "messageId": head['messageId'],
                },
                "endpoint": {"endpointId": endpoint['endpointId']},
                "payload": {"data": "AgAAAAAAAAAAAAAAAAAAAA=="},
            }})
        raise AssertionError(f"Unexpected request route: {url!r}")

    def close(self):
        pass


class ProtocolTests(unittest.TestCase):
    def test_invalid_hub(self):
        self.assertTrue(api.valid_hub(demo_hub()))
        self.assertFalse(api.valid_hub({"endpointId": "e", "mac": ""}))

    def test_macro_is_not_truncated(self):
        self.assertIsNone(api.extract_code({"codeList": [{"code": "01"}, {"code": "02"}]}))
        self.assertEqual(api.extract_code({"codeList": [{"code": "01"}]}), "01")

    def test_auth_discovery_and_send_payload(self):
        driver = api.BroadlinkCloudAPI()
        fake = FakeHttpClient()
        driver.client.close()
        driver.client = fake
        try:
            self.assertEqual(driver.login('demo@example.com', 'demo-password'), 'account-id')
            hubs, commands = driver.discover()
            self.assertEqual(len(hubs), 1)
            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0].remote_name, "Keukenlamp")
            self.assertEqual(commands[0].name, "Power")
            self.assertEqual(commands[0].code, "26005000")
            driver.send_code(commands[0])
            _, sent = fake.requests[-1]
            directive = sent['json']['directive']
            self.assertEqual(directive['header']['name'], 'commonControl')
            self.assertIn('timstamp', directive['header'])
            self.assertEqual(directive['endpoint']['endpointId'], 'demo-hub')
            self.assertEqual(
                base64.b64decode(directive['payload']['data']),
                bytes.fromhex('0200000026005000'),
            )
        finally:
            driver.close()


if __name__ == '__main__':
    unittest.main()
