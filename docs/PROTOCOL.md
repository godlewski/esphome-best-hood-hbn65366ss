# Best HBN65366SS Bluetooth protocol

Mapped on one HBN65366SS (hood firmware `4.2.2` / `1.1.20`) from a Bluetooth capture of the BEST
Kitchen app and live tests from an ESP32. The connection steps come from
[WheapLabs/esphome-best-hood](https://github.com/WheapLabs/esphome-best-hood); how the rest was
found is in [LOG.md](LOG.md).

## Connecting

1. **Wake the hood.** It doesn't advertise until it hears a BLE advertisement with manufacturer
   data `65 56 E4 D6 14 27 35 47` (company ID `0x5665`, little-endian, then 6 fixed bytes). Keep
   broadcasting it.
2. **Find it.** It then advertises as `BEST HBN65366SS`. On this unit the Bluetooth address was the
   hood's Wi-Fi MAC + 2.
3. **Connect and encrypt without bonding** (Just Works, no bond). The hood drops the link if asked
   to store a bond, so encryption is set up again on every connection.
4. **One connection at a time.** While the ESP32 is connected, the app reaches the hood through the
   cloud instead.

Pairing failed below about −85 dBm; keep the ESP32 within a few metres of the hood.

## Values

All values are **ASCII text**. Write a single digit (`"1"` = `0x31`); the hood's reads and
notifications add a trailing NUL (`31 00`). Every characteristic below supports read, write and
notify (props `0x1a`), and the hood notifies changes made with its own buttons too.

Main service `47e36221-a32f-4980-bf17-341fd4f20000`. Characteristics are
`47e36221-a32f-4980-bf17-341fd4f` + the suffix.

| Suffix | What | Values |
|---|---|---|
| `21001` | Fan on/off | `0` / `1`. Writing `1` starts at speed 1 |
| `21005` | Fan speed | `0` = off, `1`–`4`. Writing a speed turns the fan on |
| `21020` | Light on/off | `0` / `1`. Turning on restores the last level. Any odd value turns it on and any even value turns it off |
| `21026` | Light level | `1`–`4`; reads `0` while the light is off |
| `21050` | Delay off | `1` starts a delayed stop. **`0` stops the fan immediately** |
| `21040` | SmartSense | `0` / `1` |
| `21043` | (follows the fan) | `1` with the fan off, `2` with it on |
| `21017` | (follows delay off) | `4` while a delayed stop runs, `0` after |
| `11065` | Model | `HBN65366SS` (read-only) |

The app sets the light the same way: `21020` = `1`, then `21026` = level.

**Don't write `21042`.** Writing `1` made the hood drop the connection. It reads `2`; its meaning is
unknown.

Not mapped yet: `21025`, `21097` (reads `0`), `21003`, `21004`, `21022`, `21090`–`21096`
(`21096` reads `360000`), and the `11xxx` device-info group (firmware versions, `BEST`, a device
ID).

## The 40-characteristic limit

The hood has **54 characteristics**. By default ESP-IDF's GATT client caches only 40
(`CONFIG_BT_GATTC_MAX_CACHE_CHAR`), so on an ESP32 the last ones, including **`21026` and `21050`**,
silently don't exist, and ESPHome logs `Cannot poll, not connected` for them. Raise the limit:

```yaml
esp32:
  framework:
    type: esp-idf
    sdkconfig_options:
      CONFIG_BT_GATTC_MAX_CACHE_CHAR: "100"
```

Other Best models with more than 40 characteristics probably hit the same limit.

## Other services

| Service | What |
|---|---|
| `45e36221-a32f-4980-bf17-341fd4f291e0` | Wi-Fi setup: `291e1` network name, `291e2` (write-only, presumably the password), `291e3` status (`1<TAB>1<TAB><RSSI><TAB><network name>`, notified about once a second) |
| `46e36221-…-341fd4f291e0`, `44e36221-…-341fd4f291e0` | Unknown; the app subscribes to `46e…291e7` |
| `2fc251d4-7a34-11ec-90d6-0242ac120003` | Unknown |

**`291e3` contains your Wi-Fi network name.** Don't share Bluetooth captures or logs of it.
