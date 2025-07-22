# Hurricane Simulator

This Python simulation generates an irregular polygon model of a hurricane moving from the Caribbean towards Florida, publishing wind field polygons to MQTT topics.

## Features

- 5 wind speed levels (L1 to L5)
- Irregular polygon geometry with directional asymmetry
- Dynamic radius scaling with wind speed fluctuations
- MQTT publishing to topics `hurricane/data.Ln` with custom JSON messages
- Configurable update interval and simulation duration
- MQTT authentication support (username/password)

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the simulation:

```bash
python hurricane_simulator.py --broker YOUR_BROKER_IP --port 1883 --username admin --password admin --interval 10 --duration 600
```

- `--broker`: MQTT broker hostname or IP (default: localhost)
- `--port`: MQTT broker port (default: 1883)
- `--username`: MQTT username (optional)
- `--password`: MQTT password (optional)
- `--interval`: Update interval in seconds (default: 10)
- `--duration`: Total simulation time in seconds (default: 600)

The simulator publishes GeoJSON-like polygon messages with `"action": "PUT"` to topics like:

- `hurricane/data.L1`
- `hurricane/data.L2`
- `hurricane/data.L3`
- `hurricane/data.L4`
- `hurricane/data.L5`

## Notes

- The simulation emits console logs when wind levels cease to exist.
- Suitable for visualization in MQTT-enabled GIS dashboards or custom clients.

Enjoy!
