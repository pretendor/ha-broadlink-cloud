"""Minimal unofficial BroadLink EU cloud protocol client.

This is a development preview. Only single-code IR/RF commands are supported.
The client is synchronous: in Home Assistant all calls run in an executor.
"""

from __future__ import annotations

import base64
import binascii
import json
import threading
import time
from dataclasses import dataclass

import httpx

from .auth import BroadlinkAuth

BASE_URL = "https://app-service-deu-6dc239d5.ibroadlink.com"
APP_VERSION = "1.8.33.1a7fbc2ce"
SDK_LICENSE = (
    "XtpgACWuUFcYHaqiEk95t2wiEUaVgDbdm0MtQp5owJTWQbqjHLP46QRO/uZNfe0oclcgXAAAAAAygcbadDq9A72sMSyv3i+zUDfIrMkRKPdWOeDfqdEWwCTBt6/f7KAScKhmP5XJhzUJgVPNWb8gShFuD8z4NFgAsEkbxXTfoUSQjDzWcfVjcAAAAAA="
)


class BroadlinkCloudError(Exception):
    """Cloud response is invalid, unsupported or refused."""


class BroadlinkLoginError(BroadlinkCloudError):
    """Login failed or no valid session was returned."""


@dataclass(frozen=True)
class Hub:
    """One physical BroadLink hub and its cloud metadata."""

    family_id: str
    name: str
    raw: dict

    @property
    def endpoint_id(self) -> str:
        return self.raw["endpointId"]


@dataclass(frozen=True)
class Command:
    """One learned command associated with a virtual remote."""

    family_id: str
    hub: Hub
    remote_id: str
    remote_name: str
    name: str
    code: str
    position: int


def label(device: dict) -> str:
    """Get a safe-ish user-facing device label."""

    return (
        device.get("friendlyName")
        or device.get("name")
        or device.get("devName")
        or "Onbekend apparaat"
    )


def valid_hub(device: dict) -> bool:
    """Verify the fields required by the tested cloud control request."""

    fields = ("endpointId", "productId", "mac", "cookie")
    if not all(
        isinstance(device.get(field), str) and device[field].strip()
        for field in fields
    ):
        return False
    flag = device.get("devicetypeFlag")
    if type(flag) is not int or flag < 0:
        return False
    try:
        cookie = json.loads(
            base64.b64decode(device["cookie"], validate=True).decode("utf-8")
        )
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(cookie, dict)
        and type(cookie.get("terminalid")) is int
        and cookie["terminalid"] >= 0
        and isinstance(cookie.get("aeskey"), str)
        and bool(cookie["aeskey"])
    )


def extract_code(command: dict) -> str | None:
    """Accept exactly one usable code; do not silently truncate sequences."""

    entries = command.get("codeList")
    if not isinstance(entries, list) or len(entries) != 1:
        return None
    entry = entries[0]
    if not isinstance(entry, dict):
        return None
    value = entry.get("code")
    if not isinstance(value, str) or not value or len(value) > 131072:
        return None
    if len(value) % 2:
        return None
    try:
        bytes.fromhex(value)
    except ValueError:
        return None
    return value


class BroadlinkCloudAPI:
    """Stateful BroadLink EU cloud session and remote command discovery."""

    LICENSE_ID = BroadlinkAuth.LICENSE_ID

    def __init__(self) -> None:
        self.user_id: str | None = None
        self.login_session: str | None = None
        self.hubs: list[Hub] = []
        self.commands: list[Command] = []
        self.client = httpx.Client(timeout=15, follow_redirects=False)
        self._lock = threading.Lock()
        self._last_send_second = 0

    def _headers(self, family_id: str | None = None) -> dict[str, str]:
        if not self.user_id or not self.login_session:
            raise BroadlinkLoginError("Account is not connected")
        headers = {
            "userid": self.user_id,
            "loginsession": self.login_session,
            "licenseid": self.LICENSE_ID,
            "language": "en-us",
            "appVersion": APP_VERSION,
            "timestamp": str(int(time.time())),
            "messageId": str(int(time.time() * 1000)),
        }
        if family_id is not None:
            headers.update(
                {
                    "familyid": str(family_id),
                    "lid": self.LICENSE_ID,
                    "content-type": "application/json",
                }
            )
        return headers

    def login(self, email: str, password: str) -> str:
        """Log in and return a stable user ID (never print credentials)."""

        auth = BroadlinkAuth.encrypt_login(email, password)
        headers = {
            "timestamp": auth["timestamp"],
            "token": auth["token"],
            "email": email,
            "lid": self.LICENSE_ID,
            "licenseId": self.LICENSE_ID,
            "content-type": "application/x-java-serialized-object",
            "system": "android",
            "appPlatform": "android",
            "language": "en-us",
            "appVersion": APP_VERSION,
            "messageId": str(int(time.time() * 1000)),
        }
        response = self.client.post(
            BASE_URL + "/account/login", headers=headers, content=auth["body"]
        )
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError as exc:
            raise BroadlinkLoginError("Invalid login response") from exc
        if not isinstance(result, dict) or result.get("error") != 0:
            raise BroadlinkLoginError("BroadLink rejected the login")
        user_id = result.get("userid")
        session = result.get("loginsession")
        if not user_id or not session:
            raise BroadlinkLoginError("No session returned by cloud")
        self.user_id = str(user_id)
        self.login_session = str(session)
        return self.user_id

    def _query(self, path: str, family_id: str | None, body: object) -> dict:
        """Make a request with the previously tested common headers."""

        headers = self._headers(family_id)
        if body is None:
            response = self.client.post(BASE_URL + path, headers=headers, content=b"")
        else:
            response = self.client.post(BASE_URL + path, headers=headers, json=body)
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError as exc:
            raise BroadlinkCloudError("Invalid cloud JSON response") from exc
        if not isinstance(result, dict) or result.get("status") != 0:
            raise BroadlinkCloudError("Cloud request rejected")
        return result

    def get_families(self) -> list[dict]:
        """Discover all households; uses the proven Windows API path."""

        result = self._query("/appsync/group/member/getfamilylist", None, None)
        data = result.get("data")
        families = data.get("familyList") if isinstance(data, dict) else None
        if not isinstance(families, list) or not all(
            isinstance(f, dict) for f in families
        ):
            raise BroadlinkCloudError("Invalid family list")
        return families

    def get_devices(self, family_id: str) -> list[dict]:
        """Discover endpoints in one household."""

        result = self._query(
            "/appsync/group/dev/query?action=select", family_id, {"pids": []}
        )
        data = result.get("data")
        devices = data.get("endpoints") if isinstance(data, dict) else None
        if not isinstance(devices, list) or not all(
            isinstance(d, dict) for d in devices
        ):
            raise BroadlinkCloudError("Invalid device list")
        return devices

    def get_remote(self, family_id: str, endpoint_id: str) -> dict | None:
        """Return remote data or None for a physical non-remote hub."""

        result = self._query(
            "/appsync/group/ircode/query", family_id, {"endpointId": endpoint_id}
        )
        data = result.get("data")
        if not isinstance(data, dict) or data.get("endpointId") != endpoint_id:
            return None
        commands = data.get("irData")
        if commands is not None and not isinstance(commands, list):
            raise BroadlinkCloudError("Invalid remote commands")
        return data

    def discover(self) -> tuple[list[Hub], list[Command]]:
        """Discover hubs and buttons; support one hub per household for now.

        We never assume that every physical-looking endpoint is a hub.
        If there are multiple hubs in a household, no automatic command mapping
        is attempted, to avoid sending signals from the wrong room.
        """

        hubs: list[Hub] = []
        commands: list[Command] = []
        for family in self.get_families():
            family_id = family.get("familyid") or family.get("familyId")
            if family_id is None:
                continue
            family_id = str(family_id)
            devices = self.get_devices(family_id)
            family_hubs = [
                Hub(family_id, label(dev), dev)
                for dev in devices
                if valid_hub(dev)
            ]
            hubs.extend(family_hubs)
            # Only create operational controls when we can choose the correct
            # physical hub without guessing. This matches the user's setup.
            if len(family_hubs) != 1:
                continue
            hub = family_hubs[0]
            for device in devices:
                endpoint_id = device.get("endpointId")
                if not isinstance(endpoint_id, str) or not endpoint_id:
                    continue
                try:
                    remote = self.get_remote(family_id, endpoint_id)
                except BroadlinkCloudError:
                    continue  # Some endpoints cannot be queried as a remote.
                if remote is None:
                    continue
                for index, raw_cmd in enumerate(remote.get("irData") or []):
                    if not isinstance(raw_cmd, dict):
                        continue
                    name = raw_cmd.get("name") or raw_cmd.get("function")
                    code = extract_code(raw_cmd)
                    if not isinstance(name, str) or not name or not code:
                        continue
                    commands.append(
                        Command(
                            family_id=family_id,
                            hub=hub,
                            remote_id=endpoint_id,
                            remote_name=label(device),
                            name=name,
                            code=code,
                            position=index,
                        )
                    )
        self.hubs = hubs
        self.commands = commands
        return hubs, commands

    def send_code(self, command: Command) -> None:
        """Send one saved command using the payload verified on Windows."""

        hub = command.hub.raw
        if not valid_hub(hub):
            raise BroadlinkCloudError("Missing valid physical hub credentials")
        if hub.get("endpointId") != command.hub.endpoint_id:
            raise BroadlinkCloudError("Invalid hub selection")
        try:
            creds = json.loads(
                base64.b64decode(hub["cookie"], validate=True).decode("utf-8")
            )
        except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
            raise BroadlinkCloudError("Invalid paired hub cookie") from exc
        paired_cookie = base64.b64encode(
            json.dumps(
                {
                    "device": {
                        "id": creds["terminalid"],
                        "key": creds["aeskey"],
                        "aeskey": creds["aeskey"],
                        "did": hub["endpointId"],
                        "pid": hub["productId"],
                        "mac": hub["mac"],
                    }
                },
                separators=(",", ":"),
            ).encode("utf-8")
        ).decode("ascii")

        with self._lock:
            # The tested wire format uses timestamps with second resolution.
            # Keep sequential messages at least a second apart to ensure
            # distinct message IDs without changing the upstream format.
            seconds = int(time.time())
            if seconds <= self._last_send_second:
                time.sleep(self._last_send_second + 1 - seconds)
                seconds = int(time.time())
            self._last_send_second = seconds
            stamp = str(seconds)
            msg_id = f'{hub["endpointId"]}-{stamp}'
            encoded_code = base64.b64encode(
                bytes.fromhex("02000000") + bytes.fromhex(command.code)
            ).decode("ascii")
            # The misspelling `timstamp` is required by upstream.
            request = {
                "directive": {
                    "header": {
                        "namespace": "DNA.TransmissionControl",
                        "name": "commonControl",
                        "interfaceVersion": "2",
                        "messageId": msg_id,
                        "timstamp": stamp,
                    },
                    "endpoint": {
                        "devicePairedInfo": {
                            "did": hub["endpointId"],
                            "pid": hub["productId"],
                            "mac": hub["mac"],
                            "devicetypeflag": hub["devicetypeFlag"],
                            "cookie": paired_cookie,
                        },
                        "endpointId": hub["endpointId"],
                        "cookie": {},
                    },
                    "payload": {"data": encoded_code, "notpadding": 0},
                }
            }
            response = self.client.post(
                BASE_URL + "/device/control/v2/sdkcontrol",
                params={"license": SDK_LICENSE},
                headers=self._headers(command.family_id),
                json=request,
                timeout=10,
            )
            response.raise_for_status()
            try:
                result = response.json()
            except ValueError as exc:
                raise BroadlinkCloudError("Invalid control response") from exc
            event = result.get("event") if isinstance(result, dict) else None
            if not isinstance(event, dict):
                raise BroadlinkCloudError("Cloud did not acknowledge command")
            head = event.get("header")
            endpoint = event.get("endpoint")
            payload = event.get("payload")
            if (
                not isinstance(head, dict)
                or head.get("namespace") != "DNA.TransmissionControl"
                or head.get("name") != "Response"
                or head.get("interfaceVersion") != "2"
                or head.get("messageId") != msg_id
                or not isinstance(endpoint, dict)
                or endpoint.get("endpointId") != hub["endpointId"]
                or not isinstance(payload, dict)
                or payload.get("data") != "AgAAAAAAAAAAAAAAAAAAAA=="
            ):
                raise BroadlinkCloudError("Cloud did not confirm command")

    def close(self) -> None:
        """Release the HTTP connection."""

        self.client.close()
