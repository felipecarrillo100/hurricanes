# Hurricane Simulator

This Python simulation generates irregular polygon models of multiple hurricanes moving from the Caribbean towards Florida, publishing wind field polygons to MQTT topics continuously in an infinite loop.

## Features

- Simulates multiple hurricanes simultaneously (e.g., Marie and Jane)
- 5 wind speed levels (L1 to L5)
- Irregular polygon geometry with directional asymmetry
- Dynamic radius scaling with wind speed fluctuations
- MQTT publishing to topics `producers/hurricane/data/{name}/{level}/{unique_id}` with custom JSON messages
- Continuous simulation running infinitely until manually stopped
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

> **Note:** The simulation runs infinitely in a loop, repeatedly simulating the hurricane paths. The `--duration` parameter defines the length of one simulation cycle (how long it takes for the hurricanes to move from start to end positions). After each cycle completes, the simulation restarts from the beginning automatically.

The simulator publishes GeoJSON-like polygon messages with `"action": "PUT"` to topics like:

- `producers/hurricane/data/Marie/L5/L5_M5`
- `producers/hurricane/data/Jane/L3/L3_J3`
- and so on for each hurricane and wind level.

## Notes

- The simulation emits console logs when wind levels cease to exist.
- After each simulation cycle completes, a `"CLEAR"` control message is sent to reset any previous state.
- Suitable for visualization in MQTT-enabled GIS dashboards or custom clients.

Enjoy!
