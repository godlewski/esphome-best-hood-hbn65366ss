# Build log

How the HBN65366SS mapping was worked out, newest last. Real output, trimmed; addresses removed.
Some early conclusions were wrong; they're kept, marked **Correction**, because the mistake is
the useful part. The finished protocol is in [PROTOCOL.md](PROTOCOL.md).

## 2026-10-24: Wi-Fi is cloud-only

The hood joins Wi-Fi as `Broan-SoftTouch` (an Espressif MAC). A port probe of 80, 443, 6668, 6053,
8080, 1883, 8883 and 5683 found **nothing open**: the Wi-Fi side only talks to Best's cloud. So, Bluetooth.

## 2026-10-24: Upstream config, first connection

Flashed upstream `best-hood.yaml` to an ESP-WROOM-32, using **Wi-Fi MAC + 2** as the Bluetooth address
guess. It was right:

```
[I][hood]: Found 'BEST HBN65366SS' at XX:XX:XX:XX:XX:XX (RSSI -89)
[I][esp32_ble_client]: Connection open
[I][esp32_ble_client]: Service discovery complete
[I][hood]: connected, encryption requested -> 0
[E][esp32_ble_client]: auth fail reason=99
```

**Pairing failed at −86 to −97 dBm** (ESP32 on a desk in another room). Moved next to the hood:

```
[I][esp32_ble_client]: auth complete
[S][binary_sensor]: 'Bluetooth' >> ON
[S][switch]: 'SmartSense' >> ON
[S][text_sensor]: 'Model' >> 'HBN65366SS'
[W][ble_text_sensor]: [t_light_level] Cannot poll, not connected
[W][ble_text_sensor]: [t_delay_off] Cannot poll, not connected
```

Light level (`…21026`) and delay-off (`…21050`) don't exist here, like on the WCS1306SS. Switched to
upstream's WCS variant (light on/off via `…21020`), and every read now succeeds:
`'Light' >> ON`, Model, SmartSense, Bluetooth.

> **Correction:** they do exist. The ESP32 couldn't see them; see
> [the capture entry](#2026-10-24-bluetooth-capture-of-the-app-light-level-and-delay-off-found).

## 2026-10-24: Enumerating the GATT table

The app *does* set 4 light levels, so the hood must expose them somewhere. Listing the service's
characteristics from `ble_client`'s `on_connect` (ESPHome releases its parsed services shortly
after connecting, and the ESP-IDF GATT cache wasn't available) gave **32 characteristics** in
`47e36221-a32f-4980-bf17-341fd4f…`. Props `0x12` = read + notify, `0x1a` = read + write + notify.

| Suffix | Props | Baseline (light on) | Notes |
|---|---|---|---|
| 00001, 10001, 20001 | 12 | | |
| 11062–11069 | 12 | | 11065 = model |
| 11070, 11071, 11072, 11076 | 12 | | 11070 appears twice (once `1a`) |
| 21001 | 1a | | fan on/off (upstream) |
| 21003, 21004 | 12 | `0`, `0` | |
| 21005 | 1a | | fan speed (upstream) |
| 21017 | 1a | `0` | |
| 21020 | 1a | | light on/off (upstream) |
| 21022 | 12 | `3` | read-only: current light level? |
| 21040 | 1a | | SmartSense (upstream) |
| 21042 | 1a | `2` | |
| 21043 | 1a | `1` | |
| 21090, 21091 | 1a / 12 | `0`, `0` | |
| 21092–21095 | 1a / 12 | `1`, `1`, `1`, `0` | |
| 21096 | 1a | `360000` | 6 min in ms? Filter timer? |

Next: watch them all (notify + 30 s poll) while changing the light level in the app.

## 2026-10-24: Watching every characteristic during app changes

Logged every value change (notify + 15–30 s polling) while changing settings in the BEST Kitchen app.
Also logged the raw value of `…21020` before upstream's filter, which **ignores anything other than
`0`/`1`**.

App: light level 1 → 2 → 3 → 4 → off, then fan on, then delay-off.

```
12:59:28  21020 = 1 (was 0)    light on (level-1 press)
12:59:39  21020 = 0 (was 1)    light off
12:59:41  21005 = 4 (was 0)    fan on at speed 4
12:59:41  21043 = 2 (was 1)    changes together with the fan
12:59:52  21005 = 0 (was 4)    delay-off press: the app turned the vent off
```

**Levels 2–4 changed nothing** in any of the 30 characteristics watched. The `11xxx` group is
device info: `00001`/`11071` = `4.2.2`, `10001`/`11072` = `1.1.20` (firmware versions), `11064` =
`BEST`, `11062`/`11063`/`11066` = a 24-hex-digit ID, `11067`/`11068` = `1`.

The ESP32 holds the hood's Bluetooth link, so the app probably went through the cloud for these
changes. The hood then applied the level without notifying any GATT characteristic.

## 2026-10-24: What the app calls things

Static string search of the Android app's Hermes bundle (no code run). Characteristic names:
`charLightStateUUID`, **`charLightIntensityUUID`**, **`charLightOptionSelectionUUID`**,
`charLightColorUUID`, `charLightWhiteBalanceUUID`, `charAutoLightUUID`, `charAutoLightTimerUUID`,
**`charFanDelayOffStateUUID`**, plus `numberOfLightIntensities` and
`buildLightIntensitiesFromFactor`. So the number of light levels is per model.

UUID suffixes referenced by the app: `00001`, `10001`, `11062`–`11065`, `11067`, `11070`, `20000`,
`20001`, `21001`, `21005`, `21017`, `21020`, **`21024`**, **`21026`**, `21040`, `21042`, `21043`,
**`21050`**, `21090`–`21094`, `21096`, **`21097`**. Also a second service, `45e36221-…-341fd4f291e0`
to `…291e7`, likely Wi-Fi provisioning. This hood has none of `21024`, `21026`, `21050` or `21097`.

> **Correction:** they do exist. The ESP32 couldn't see them; see
> [the capture entry](#2026-10-24-bluetooth-capture-of-the-app-light-level-and-delay-off-found).

Mapping names to UUIDs needs the bundle decompiled (Hermes bytecode), which is not done yet.

## 2026-10-24: Physical controls, delay-off found, write tests

**Hood's own controls** (light via the touch slider, then fan, then delay-off), all 17 candidates
polled every 10 s plus notify:

```
13:26:34  21020 0 -> 1    light on (from the slider)
13:26:49  21001 0 -> 1    fan on
13:26:49  21005 0 -> 4    speed 4
13:26:55  21017 0 -> 4    delay-off pressed: fan keeps running
~13:38    21017 4 -> 0    delayed stop finished (about 12 min)
```

- **`…21017` is delay-off** on this model (upstream: `…21050`, which doesn't exist here). The value
  was `4` while the delayed stop ran and `0` when it finished. It might be the fan speed at the
  time; not confirmed.

> **Correction:** the app uses `…21050` for delay-off; `…21017` only reflects it.
- **Light level is never reported.** Sliding through the levels changed no characteristic. Also
  confirmed absent: `21024`, `21026`, `21050`, `21097` (empty reads).

> **Correction:** they do exist. The ESP32 couldn't see them; see
> [the capture entry](#2026-10-24-bluetooth-capture-of-the-app-light-level-and-delay-off-found).

**Write tests** (light on, someone watching the hood):

| Write | Hood reported | Light |
|---|---|---|
| `21020` = `1` | `1` | (already on) |
| `21020` = `2` | `0` | off |
| `21020` = `3` | `1` | on (fades up) |
| `21020` = `4` | `0` | off |
| `21020` = `1` | `1` | on (fades up) |
| `21042` = `1` | (none) | **hood dropped the connection** (`auth fail reason=99`); after reconnecting `21042` still read `2` |

`…21020` is on/off only (odd = on, even = off). `…21042` rejects our writes. Next: decompile the
app's Hermes bundle to see which characteristic and values it uses for brightness on this model.

## 2026-10-24: The second service is Wi-Fi provisioning

The app also uses service `45e36221-a32f-4980-bf17-341fd4f291e0`, which my first dump missed. It
has 7 characteristics:

| Suffix | Props | Content |
|---|---|---|
| 291e1 | read, write | Wi-Fi network name (32 bytes) |
| 291e2 | write only | (presumably the Wi-Fi password) |
| 291e3 | read, notify | Wi-Fi status: `1<TAB>1<TAB><RSSI><TAB><network name>` |
| 291e4, 291e5, 291e7 | read, write, notify | `0` |
| 291e6 | read, notify | empty |

No light level here either. Watchers removed (they would only log the network name).

Delay-off is wired as a read-only `Delay off` binary sensor (`…21017` > 0). Which value *starts* a
delayed stop is still unknown; test buttons write `1` and `0`.

## 2026-10-24: Bluetooth capture of the app: light level and delay-off found

The app's traffic, captured on an Android 12 phone with the Bluetooth HCI
snoop log. ESP32 unplugged so the app had the hood to itself; phone Wi-Fi and mobile data off so
the app had to use Bluetooth.

1. *Developer options → Enable Bluetooth HCI snoop log*, then Bluetooth off and on.
2. In the app: light on, levels 1, 2, 3, 4, 1, light off, fan on, delay-off, fan off, about 10 s
   apart.
3. `adb bugreport bugreport.zip` (the log itself needs root), then
   `unzip -j bugreport.zip FS/data/misc/bluetooth/logs/btsnoop_hci.log`.
4. `python3 tools/btsnoop_att.py btsnoop_hci.log` prints the handle → UUID map and every ATT write
   and notification. The capture itself is not in this repo: the Wi-Fi status notifications in it
   include the network name.

The writes (values are ASCII; the hood's notifications add a trailing NUL):

```
15:46:54.605 -> WRITE_REQ 21020 "1"     light on
15:46:54.719 <- NOTIFY    21020 "1"
15:46:54.943 <- NOTIFY    21026 "4"     the hood restores the last level
15:46:56.588 -> WRITE_REQ 21026 "1"     level 1
15:46:58.701 -> WRITE_REQ 21026 "2"     level 2
15:47:00.754 -> WRITE_REQ 21026 "3"     level 3
15:47:02.783 -> WRITE_REQ 21026 "4"     level 4
15:47:04.600 -> WRITE_REQ 21026 "1"     level 1
15:47:06.991 -> WRITE_REQ 21020 "0"     light off
15:47:07.229 <- NOTIFY    21026 "0"
15:47:09.152 -> WRITE_REQ 21001 "1"     fan on (21005 -> 1, 21043 -> 2)
15:47:12.261 -> WRITE_REQ 21050 "1"     delay-off
15:47:14.741 -> WRITE_REQ 21001 "0"     fan off
```

So this hood **does** have `…21026` (light level 1–4) and `…21050` (delay-off), same as upstream's
HBN1306SS, plus `21025` and `21097`. The capture lists **54 characteristics**; my ESP32 dump showed
only the first ones. **Cause:** ESP-IDF's GATT client caches 40 characteristics by default
(`CONFIG_BT_GATTC_MAX_CACHE_CHAR`), so the last ones were silently missing and ESPHome logged
"Cannot poll" for them. My earlier "doesn't exist on this model" conclusions were wrong. With
`CONFIG_BT_GATTC_MAX_CACHE_CHAR: "100"` the ESP32 lists all four:

```
CHAR 47E36221-A32F-4980-BF17-341FD4F21025 handle 0x0094 props 0x1a
CHAR 47E36221-A32F-4980-BF17-341FD4F21026 handle 0x0097 props 0x1a
CHAR 47E36221-A32F-4980-BF17-341FD4F21097 handle 0x009a props 0x1a
CHAR 47E36221-A32F-4980-BF17-341FD4F21050 handle 0x009d props 0x1a
```

`…21017` (seen at `4` during a delayed stop) is not used by the app; the app subscribes to
21001, 21005, 21020, 21026, 21040, 21042, 21043, 21050, 21094, 21096.

## 2026-10-24: Clean firmware, tested from the ESPHome API

Discovery code removed. Light is now a dimmable light (HA brightness → level 1–4, written like the
app: `21020=1`, then `21026=level`). Delay off is a switch on `…21050`. Test via the API:

```
  light=2  -> light on, brightness 0.5
  light=1  -> 0.25
  light=3  -> 0.75
  light=4  -> 1.0
  light=0  -> off
  fan=2    -> fan on, speed 2
  delay=1  -> delay_off on
  delay=0  -> delay_off off, and the fan turned OFF 0.2 s later
```

Writing `21050=0` ends the delayed stop *immediately* (fan off) rather than cancelling it. Still to
check: how long a delayed stop runs before the fan stops by itself.

## 2026-10-24: The hood's own buttons

Fan, light and light level changed with the hood's own controls all showed up in Home Assistant.
