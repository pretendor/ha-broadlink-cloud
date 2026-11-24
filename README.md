# BroadLink Cloud for Home Assistant (Unofficial)

[![Open this repository in Home Assistant Marketplace / HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pretendor&repository=ha-broadlink-cloud&category=integration)

An **unofficial** Home Assistant custom integration for the **European BroadLink Cloud** service used by the modern BroadLink phone app. It exposes commands saved in the app as native **Home Assistant `button` entities**. The cloud route works independently of the official *local* BroadLink integration.

> [!IMPORTANT]
> This is a community project and is **not affiliated with BroadLink or Home Assistant**. It uses an undocumented cloud API which may change without notice. Do not confuse these buttons with a measured on/off state.

## Features

- Connect with the account used in the official BroadLink mobile app (EU region only).
- Discover homes, physical hubs, and virtual IR/RF remote controls.
- Create one `button` entity for each supported **single-code** remote action.
- Send button presses through BroadLink Cloud to a paired RM hub.
- Device hierarchy in Home Assistant links virtual remotes to the discovered hub.
- Dutch and English translations.
- No additional cloud account, subscription or automation server required.

### Verified / limitations

- **Field tested** with one EU BroadLink account and an **RM Pro+**, including light and TV commands from Home Assistant.
- Other regions and RM models are **not yet validated**. Only one physical hub per household is currently auto-mapped: multiple hub households require future work.
- Multi-code macros are omitted rather than silently truncated; unsupported device types do not become buttons.
- Devices are exposed as buttons **only**. No `light`, `switch`, `media_player`, or physical state measurement.
- Remote commands can be learnt and edited in the official BroadLink app, not through this integration.
- A cloud acknowledgment means a request was accepted; it does not prove an appliance's real state.
- Cloud sessions are established when Home Assistant loads the integration. Automatic recovery from an expired session is not yet implemented.

## Install (Home Assistant 2026.11+ Marketplace)

1. Open the [Marketplace/HACS repository link](https://my.home-assistant.io/redirect/hacs_repository/?owner=pretendor&repository=ha-broadlink-cloud&category=integration) or go to **Settings → Marketplace**.
2. If this integration is not in the catalog yet, **add it as a custom repository** using this GitHub URL: `https://github.com/pretendor/ha-broadlink-cloud`. Select type **Integration**.
3. Install **BroadLink Cloud (Unofficial)** and restart Home Assistant if prompted.
4. Go to **Settings → Devices & services → Add integration** and search for **BroadLink Cloud (Unofficial)**.
5. Sign in with your BroadLink account in the **EU** region. Open the discovered devices and click a command button.

## Install (older Home Assistant + HACS)

In HACS open **Custom repositories**, add `https://github.com/pretendor/ha-broadlink-cloud` as type **Integration**, and download it. Restart Home Assistant, then add the integration in **Settings → Devices & services**.

## Manual installation

Copy the complete `custom_components/broadlink_cloud/` folder to your Home Assistant's `config/custom_components/broadlink_cloud/` folder; restart and add the integration.

## Known issues and security

- A Power button often sends a **toggle**; don't press it repeatedly when unsure of its state.
- No sensor/status information is provided. The activity log only records button presses.
- Cloud requires internet access and the official BroadLink phone app account. Current cloud protocol has been tested only with an EU account.
- The Home Assistant configuration entry **stores your BroadLink password** for re-login. Protect backups and the `.storage` directory. Never attach those files to issues.
- **Never post** passwords, login sessions, raw API responses, device cookies, MAC addresses, IDs or learnt IR/RF code payloads. Redact logs before sharing.
- The crypto/login protocol is borrowed from an existing open-source reverse-engineering effort; do not treat this as an official BroadLink SDK or public API.

## Reporting issues

Use [GitHub Issues](https://github.com/pretendor/ha-broadlink-cloud/issues) with your Home Assistant version, device model, region, what action failed and **redacted** logs. Do not include identifiers, secrets or code values.

## Development

The repository includes offline tests that do not contact your BroadLink account:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install httpx==0.28.1 cryptography
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Automated GitHub Actions run offline tests, HACS validation and hassfest. Passing offline tests is **not** a substitute for testing inside Home Assistant.

## Maintainer publication instructions

See [PUBLISHING.md](PUBLISHING.md) for publishing under your GitHub account, making a release and requesting catalog inclusion.

## Attribution and license

The unofficial BroadLink EU cloud protocol was ported to Python with attribution to [skymike/homebridge-broadlink-cloud](https://github.com/skymike/homebridge-broadlink-cloud) (© 2026 skymike), MIT-licensed. This repository includes the MIT notice in [LICENSE](LICENSE). Neither author is affiliated with BroadLink.
