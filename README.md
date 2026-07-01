# WNC AF55 for Home Assistant

Home Assistant custom integration for the **WNC AF55 Outdoor 4G/5G modem**.
It communicates directly with the modem over the local network; no cloud service
is required.

The integration reproduces the AF55 web interface protocol, including its
password encoding, `CGISID` session cookie, CGI token handling and confirmed
reboot command.

## Features

- Local polling through the AF55 HTTPS interface
- Configuration through the Home Assistant UI
- Automatic login, session renewal and reauthentication
- Clean logout when Home Assistant stops or reloads the integration
- 4G/5G connection state and bearer type
- NR and LTE RSRP/RSRQ values
- AF55 graphical signal-quality level
- Public IPv4, APN, provider, roaming and radio mode
- Mobile-session start and readable session duration
- Persistent IP-change and session metadata across Home Assistant restarts
- 60-second debounce for transient `NULL` bearer states
- Reboot button for dashboards and scheduled automations
- Redacted diagnostics
- English and Dutch translations

## Supported hardware and firmware

This integration was developed and tested against a T-Mobile Netherlands / Odido
WNC AF55 Outdoor running firmware in the `v01.10.50.00_perf` family.
Other AF55 provider variants may use different API fields or behaviour.

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add:

   ```text
   https://github.com/pascalsaul/home-assistant-af55
   ```

4. Select category **Integration**.
5. Install **WNC AF55**.
6. Restart Home Assistant.
7. Open **Settings → Devices & services → Add integration**.
8. Search for **WNC AF55**.

## Manual installation

Copy this directory:

```text
custom_components/af55
```

to:

```text
/config/custom_components/af55
```

Restart Home Assistant and add the integration through **Devices & services**.

## Configuration

Default values:

- Host: `192.168.1.1`
- Username: `admin`
- TLS certificate verification: disabled
- Polling interval: 30 seconds

The host can be changed during setup if the AF55 uses another management IP,
such as `192.168.0.254`.

The modem normally uses a self-signed certificate, so certificate verification
must remain disabled unless the AF55 has been configured with a trusted
certificate.

## Entities

The exact entity IDs depend on the Home Assistant naming configuration.
Typical entities include:

- Connection type
- Connected
- Connected to 5G
- Signal quality
- Signal strength
- NR RSRP / NR RSRQ
- LTE RSRP / LTE RSRQ
- Public IPv4
- Last public IP change
- APN
- Provider
- Radio mode
- Roaming
- Mobile session duration
- Mobile session start
- Reboot modem

The mobile-session-duration entity has a readable state such as:

```text
1d 03h 14m 09s
```

Its attributes also retain the raw modem value, numeric duration and session
start.

## Scheduled reboot example

```yaml
alias: AF55 nightly reboot
triggers:
  - trigger: time
    at: "04:00:00"
actions:
  - action: button.press
    target:
      entity_id: button.wnc_af55_outdoor_reboot_modem
mode: single
```

Use the actual reboot-button entity ID from your installation.

## Recorder recommendation

The readable session duration changes every polling cycle. Exclude this entity
from Recorder when its detailed history is not needed:

```yaml
recorder:
  exclude:
    entities:
      - sensor.wnc_af55_outdoor_mobile_session_duration
```

Use the actual entity ID from your installation.

## Important behaviour

- Some AF55 firmware permits only one active administrator session. Keeping the
  modem web interface open can temporarily compete with Home Assistant.
- A local modem reboot can restart the mobile session while retaining the same
  public IPv4 address.
- `Last public IP change` only updates when the modem actually reports a
  different address.
- Short one-poll `NULL` bearer states are suppressed for 60 seconds to reduce
  false disconnect/reconnect events. Longer outages remain visible.
- The AF55 API is undocumented and provider-specific. Future firmware may
  require integration updates.

## Diagnostics and privacy

Home Assistant diagnostics redact credentials, public IP addresses, tokens,
IMEI, IMSI and MAC-address-like values. Credentials are stored in the Home
Assistant config entry; protect Home Assistant backups and the `.storage`
directory.

## Development

Validate Python syntax:

```bash
python -m compileall custom_components/af55
```

The repository includes HACS and hassfest validation workflows.

## License

MIT
