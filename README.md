# Laica Smart Scale : Home Assistant Integration ⚖️

Use your **Laica smart scale** with **Home Assistant** via **Bluetooth Low Energy (BLE)** - no pairing required.
When you step on the scale, it broadcasts data and Home Assistant picks it up locally.

## What you get

- **Weight** sensor
- **Impedance** sensor (from the scale, when available)
- **Last seen** sensor (helpful for troubleshooting)

## What you need

- Home Assistant (Core / OS / Supervised)
- A working Bluetooth setup in Home Assistant:
  - Built-in Bluetooth on the machine running HA, **or**
  - A supported USB Bluetooth adapter, **or**
  - An **ESPHome Bluetooth Proxy** nearby (recommended for better range)

## Install (recommended): HACS 🧩

1. Install **HACS** if you don’t have it yet.
2. In Home Assistant, open **HACS → Integrations**.
3. Open the menu (⋮) → **Custom repositories**.
4. Add this repository URL, and choose category **Integration**:
   - `https://github.com/nielsmaerten/ha-laica-smart-scale`
5. Find **“Laica Smart Scale (BLE)”** in HACS and click **Download**.
6. Restart Home Assistant 🔄
7. Step on the scale while it’s in range ✅ Home Assistant should discover it automatically.

If it doesn’t show up automatically: go to **Settings → Devices & services → Add integration**, search for **Laica Smart Scale (BLE)**, and enter the scale’s Bluetooth address (usually printed on a sticker on the scale itself, or in the manual/box).

## Install (manual) 🛠️

1. Download this repository (as a ZIP) and extract it.
2. Copy the folder:
   - from: `custom_components/laica_smart_scale`
   - to: `<your Home Assistant config>/custom_components/laica_smart_scale`
3. Restart Home Assistant 🔄
4. Step on the scale while it’s in range ✅ Home Assistant should discover it automatically.

If it doesn’t show up automatically: go to **Settings → Devices & services → Add integration**, search for **Laica Smart Scale (BLE)**, and enter the scale’s Bluetooth address (usually printed on a sticker on the scale itself, or in the manual/box).

If you’re not sure where your “config” folder is: in Home Assistant go to **Settings → System → Storage** and look for the **Configuration directory** path.

## Using it ✅

- Step on the scale (a measurement broadcast is sent when it’s in use).
- Open **Settings → Devices & services** and select the **Laica Smart Scale (BLE)** device to see the created sensors.

## Troubleshooting 🔎

- **No values show up**
  - Make sure Home Assistant has Bluetooth working: check **Settings → Bluetooth**.
  - Move the scale closer to your HA Bluetooth adapter / Bluetooth Proxy.
  - Try again after restarting Home Assistant.
- **Discovery doesn’t find the scale**
  - Add the integration manually and enter the scale’s Bluetooth address.

## Previous work

This integration is based on work from the `ble_monitor` community: `https://github.com/custom-components/ble_monitor/pull/804`.

## License

MIT
