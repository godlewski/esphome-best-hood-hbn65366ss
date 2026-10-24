# Best HBN65366SS range hood → Home Assistant (local Bluetooth)

> [!CAUTION]
> **Use at your own risk.** This is a hobby project shared as-is, with no warranty of any kind. I am
> not responsible for any damage, voided warranty or other loss that results from using this code,
> these instructions or the hardware described here. You alone are responsible for how you build
> and use it. See the [license](LICENSE).

**Control a Best by Broan HBN65366SS range hood from Home Assistant without the cloud**, with an
ESP32 running ESPHome that talks to the hood over Bluetooth. No wiring into the hood, and the BEST
Kitchen app keeps working.

- **Fan:** on/off and all 4 speeds.
- **Light:** on/off and all 4 levels.
- **Delay off** and **SmartSense**.
- **Two-way:** changes made on the hood or in the app show up in Home Assistant.

> [!NOTE]
> **Built with AI.** I worked this out and wrote the config and these docs together with an AI
> coding agent (Claude Code), and tested each step on my own hood. The [build log](docs/LOG.md)
> shows how, including what didn't work. Review it before you trust it, like any code you find
> online.

This builds on [WheapLabs/esphome-best-hood](https://github.com/WheapLabs/esphome-best-hood), which
found how to wake, pair with and control Best hoods on the HBN1306SS and WCS1306SS (see
[NOTICE.md](NOTICE.md)). On the HBN65366SS, the light level and delay-off only show up after raising
an ESP-IDF limit, which this config does ([why](docs/PROTOCOL.md#the-40-characteristic-limit)).

The fix for that limit is being contributed back upstream, since it likely affects their models too.

Unofficial; not affiliated with or endorsed by Best or Broan-NuTone.

---

## Does it work with my hood?

**Tested with exactly one hood:** a **Best HBN65366SS** (36" built-in insert), hood firmware
`4.2.2` / `1.1.20`.

| Feature | Status |
|---|---|
| Fan on/off and 4 speeds | ✅ |
| Light on/off and 4 levels | ✅ |
| Delay off | ✅ starts a delayed stop. Switching it **off stops the fan immediately** |
| SmartSense | ✅ |
| Changes made on the hood or in the app | ✅ show up in Home Assistant, including the light level |

Other Best hoods that work with the BEST Kitchen app over Bluetooth may well work too (upstream
covers the HBN1306SS and WCS1306SS). If yours advertises as `BEST <model>` and connects, compare its
characteristics with [docs/PROTOCOL.md](docs/PROTOCOL.md).

The hood's Wi-Fi is cloud-only (no open ports), which is why this uses Bluetooth.

## What you need

- An **ESP32 with Bluetooth**. Tested: a classic ESP-WROOM-32 dev board (`esp32dev`). The ESP32-S3
  and C3 have Bluetooth too, but would need a different `board:`.
- A USB power supply **within a few metres of the hood**. Pairing failed from another room
  (about −90 dBm).
- A computer with [uv](https://docs.astral.sh/uv/) (to run ESPHome as `uvx esphome …`), or the
  ESPHome add-on in Home Assistant.
- 2.4 GHz Wi-Fi.

## How it works

```
Best hood  <-- Bluetooth LE -->  ESP32 (ESPHome)  <-- Wi-Fi -->  Home Assistant
```

1. The hood stays invisible until it hears a "wake-up" advertisement, which the ESP32 broadcasts.
2. The ESP32 connects and encrypts the link **without bonding** (the hood refuses bonds).
3. Fan, light and the rest are characteristics holding ASCII digits (`"0"` to `"4"`). The ESP32
   writes them and the hood notifies every change, including ones made with its own buttons.

The hood takes one Bluetooth connection at a time. While the ESP32 holds it, the app controls the
hood through the cloud. Details: [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Setup

### 1. Get the code

```bash
git clone https://github.com/godlewski/esphome-best-hood-hbn65366ss.git
cd esphome-best-hood-hbn65366ss/esphome
uvx esphome version                       # checks that uv and ESPHome work
```

On Linux, your user needs access to the serial port (group `dialout` on Debian/Ubuntu, `uucp` on
Arch; log out and back in after adding it).

### 2. Fill in your secrets

```bash
cp secrets.yaml.template secrets.yaml
openssl rand -base64 32                   # paste as best_hood_api_key
```

Fill in your Wi-Fi name and password, the API key, and a fallback-hotspot password. Leave
`best_hood_mac` as it is for now. `secrets.yaml` is gitignored; keep it that way.

### 3. Find your hood's Bluetooth address

On the tested hood it was the **hood's Wi-Fi MAC + 2** (for example, Wi-Fi `…:10` → Bluetooth
`…:12`). The hood appears on your router as `Broan-SoftTouch`. If you have that MAC, add 2 to the
last byte and put the result in `best_hood_mac`.

Otherwise flash once with the placeholder (step 4), and the log prints every Best hood it sees:

```
[I][hood]: Found 'BEST HBN65366SS' at XX:XX:XX:XX:XX:XX (RSSI -60)
```

Put that address in `best_hood_mac` and flash again.

### 4. Flash

```bash
uvx esphome config best-hood.yaml          # validate first
uvx esphome run best-hood.yaml             # first time over USB; pick the serial port
```

Later updates go over Wi-Fi: `uvx esphome run best-hood.yaml --device <ESP32 IP>`.

### 5. Place it and check the log

Power the ESP32 within a few metres of the hood. Close the BEST Kitchen app (or turn the phone's
Bluetooth off) for the first connection. Then:

```bash
uvx esphome logs best-hood.yaml --device <ESP32 IP>
```

It's working when you see:

```
[I][esp32_ble_client]: auth complete
[S][binary_sensor]: 'Bluetooth' >> ON
[S][text_sensor]: 'Model' >> 'HBN65366SS'
```

### 6. Add it to Home Assistant

It's usually discovered: *Settings → Devices & services → ESPHome*. Otherwise add ESPHome by IP.
Enter your `best_hood_api_key`. Reserve the ESP32's IP on your router so it doesn't change.

## Home Assistant

| Entity | What |
|---|---|
| `fan.best_hood_fan` | On/off and 4 speeds |
| `light.best_hood_light` | On/off and brightness. 25 / 50 / 75 / 100 % = hood levels 1–4 |
| `switch.best_hood_delay_off` | Starts a delayed stop. Turning it off stops the fan now |
| `switch.best_hood_smartsense` | SmartSense |
| `binary_sensor.best_hood_bluetooth` | The ESP32 is connected and has read the hood |
| `sensor.best_hood_model` | The hood's model |
| `button.best_hood_reconnect` / `button.best_hood_restart` | Diagnostics |

If the device was in an area when it was added, some IDs may get an area prefix (e.g.
`switch.kitchen_best_hood_delay_off`).

**Dashboard card:** [homeassistant/dashboard-card.yaml](homeassistant/dashboard-card.yaml), standard
cards only. It has the fan with speed buttons, the light with 4 level buttons, Delay off and
SmartSense.

The ESP32 never writes to the hood before it has read the hood's state, so restarting it won't switch
anything off.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No `Found 'BEST …'` line | The hood only wakes for the ESP32's advertisement; move the ESP32 closer and wait a minute. Check the hood has power |
| `auth fail reason=99` | Signal too weak. Move the ESP32 closer (better than −85 dBm) |
| Connects, then `Cannot poll, not connected` for the light level or delay off | The ESP-IDF characteristic limit; make sure `CONFIG_BT_GATTC_MAX_CACHE_CHAR` is still in `best-hood.yaml` and rebuild clean (`uvx esphome clean best-hood.yaml`) |
| `Bluetooth` stays off while the app is open | The hood takes one connection at a time. Close the app or turn off the phone's Bluetooth |
| The fan stopped when you turned Delay off off | That's the hood: ending a delayed stop stops the fan |

## For AI agents

If you're an AI agent helping someone set this up, read [AGENTS.md](AGENTS.md) first.

## Repo layout

| Path | What |
|---|---|
| `esphome/best-hood.yaml` | The ESPHome config |
| `esphome/secrets.yaml.template` | Copy to `secrets.yaml` and fill in |
| `homeassistant/dashboard-card.yaml` | Dashboard card |
| `docs/PROTOCOL.md` | Characteristics and values |
| `docs/LOG.md` | Build log: how it was mapped, mistakes included |
| `tools/btsnoop_att.py` | Prints the Bluetooth traffic in an Android HCI snoop log (for mapping other models) |

## License

MIT. See [LICENSE](LICENSE). Based on WheapLabs/esphome-best-hood (MIT); see [NOTICE.md](NOTICE.md).
