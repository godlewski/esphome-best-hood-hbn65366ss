# Instructions for AI agents

You're helping someone set up this bridge. The human-facing guide is [README.md](README.md); this
file tells you how to run it safely.

## Ground rules

- **The person must physically do these themselves:** plug in and place the ESP32, close the BEST
  Kitchen app, and confirm what the hood actually does. Ask them, and wait for their answer.
- **Never invent values.** Wi-Fi name and password come from the person. Generate
  `best_hood_api_key` (`openssl rand -base64 32`) and `best_hood_ap_password`
  (`openssl rand -hex 16`) yourself. `best_hood_mac` comes only from the person's router (Wi-Fi MAC
  + 2, then confirmed in the log) or from the log's `Found 'BEST …' at …` line.
- **Never commit or print** `esphome/secrets.yaml`. It's gitignored. Don't paste the Wi-Fi password,
  the API key or the hood's address into chat output, issues or PRs.
- **Don't publish Bluetooth captures or raw logs of the `291e…` service:** the hood's Wi-Fi status
  includes the person's network name.
- **Ask before turning on the fan or switching Delay off off** (turning Delay off off stops the fan
  immediately), and **never write `…21042`** (it made the hood drop the connection).

## Steps

1. **Check the model.** Ask for the model on the hood's label. Proceed if it's `HBN65366SS`.
   Otherwise explain that it's untested, and compare its characteristics with
   [docs/PROTOCOL.md](docs/PROTOCOL.md).
2. **Tools.** Make sure `uv` is installed (`uvx esphome version` works). On Linux, make sure the
   user is in the serial group (`uucp` on Arch, `dialout` on Debian/Ubuntu); adding them needs sudo
   and a re-login, so tell them.
3. **Secrets.** In `esphome/`: `cp secrets.yaml.template secrets.yaml` and fill it in. Wi-Fi must be
   2.4 GHz.
4. **Bluetooth address.** Ask whether their router shows the hood (`Broan-SoftTouch`) and its MAC.
   If so, add 2 to the last byte and use that. Otherwise keep the placeholder and read it from the
   log after the first flash.
5. **Validate before flashing:** `uvx esphome config best-hood.yaml`.
6. **Flash:** `uvx esphome run best-hood.yaml --device <port> --no-logs` over USB the first time,
   then `--device <ESP32 IP>`.
7. **Verify.** Ask them to place the ESP32 within a few metres of the hood and close the app. Run
   `uvx esphome logs best-hood.yaml --device <ESP32 IP>` and wait for `auth complete` and
   `'Model' >> '<model>'`. `auth fail reason=99` means the signal is too weak.
8. **Verify control (ask first).** Toggle the light and set a level, then (with permission) the fan.
   Ask them to confirm the hood responds.
9. **Home Assistant.** Follow [README → Add it to Home Assistant](README.md#6-add-it-to-home-assistant)
   and suggest a DHCP reservation for the ESP32.

## Reading the log

| Line | Meaning |
|---|---|
| `Found 'BEST …' at …` | A hood is advertising (only shown until connected) |
| `connected, encryption requested -> 0` | Connected; encryption requested |
| `auth complete` | Encrypted; reads follow |
| `auth fail reason=99` | Pairing failed, usually weak signal |
| `fan: A -> B` / `light: A -> B` | The ESP32 is sending a Home Assistant change (light: level, 0 = off) |
| `Cannot poll, not connected` | Not connected yet, or the characteristic is missing (see the 40-characteristic limit in docs/PROTOCOL.md) |
| `Hood disconnected` | The link dropped; it reconnects by itself |
