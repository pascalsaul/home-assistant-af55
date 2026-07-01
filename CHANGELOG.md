# Changelog

## 0.2.12

- Changed the default AF55 management address to `192.168.1.1`.
- Updated repository metadata and public documentation.
- Prepared the integration for distribution through HACS as a custom repository.

## 0.2.11

- Persisted the last known public IPv4 address and its change timestamp.
- Persisted the mobile-session start timestamp.
- Persisted the last stable bearer for restart-safe debounce behaviour.

## 0.2.10

- Preserved `Last public IP change` across Home Assistant restarts.
- Stopped treating the first IP observed after startup as a new change.

## 0.2.9

- Added a 60-second debounce for transient `NULL` bearer states.

## 0.2.8

- Added graphical signal quality based on the AF55 `level` field.

## 0.2.7

- Changed mobile session duration to a readable state.

## 0.2.6

- Added modem metadata and duration attributes.
- Removed the noisy separate readable-duration entity.

## 0.2.2

- Added the confirmed reboot action `set_system_wan_power` with `reboot: 1`.

## 0.2.1

- Added clean logout and retryable handling of temporary AF55 session errors.

## 0.2.0

- Added session timing, IP-change tracking, diagnostics and reboot control.

## 0.1.1

- Fixed the AF55 single-admin-session conflict during initial setup.

## 0.1.0

- Initial release.
