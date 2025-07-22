import math
import random
import time
import json
import argparse
import geojson
from geojson import Feature
import paho.mqtt.client as mqtt


def km_to_deg(km, latitude):
    dlat = km / 110.574
    dlon = km / (111.320 * math.cos(math.radians(latitude)))
    return dlat, dlon


# New: Smoother wind field using quadrant-based interpolation
def create_asymmetric_wind_field(lat, lon, base_radius_km):
    quadrant_factors = {
        "NE": 1.2,
        "SE": 1.0,
        "SW": 0.8,
        "NW": 1.0,
    }

    quadrant_angles = {
        "NE": (0, 90),
        "SE": (90, 180),
        "SW": (180, 270),
        "NW": (270, 360),
    }

    def get_quadrant_factor(angle_deg):
        if 0 <= angle_deg < 90:
            a0, a1 = 0, 90
            f0, f1 = quadrant_factors["NE"], quadrant_factors["SE"]
        elif 90 <= angle_deg < 180:
            a0, a1 = 90, 180
            f0, f1 = quadrant_factors["SE"], quadrant_factors["SW"]
        elif 180 <= angle_deg < 270:
            a0, a1 = 180, 270
            f0, f1 = quadrant_factors["SW"], quadrant_factors["NW"]
        else:
            a0, a1 = 270, 360
            f0, f1 = quadrant_factors["NW"], quadrant_factors["NE"]
        ratio = (angle_deg - a0) / (a1 - a0)
        blend = (1 - math.cos(ratio * math.pi)) / 2  # smooth cosine interpolation
        return f0 * (1 - blend) + f1 * blend

    num_points = 64
    coords = []
    for i in range(num_points):
        angle_deg = i * (360 / num_points)
        angle_rad = math.radians(angle_deg)

        direction_factor = get_quadrant_factor(angle_deg)
        fluctuation = random.uniform(0.95, 1.05)  # subtle randomness
        adjusted_radius = base_radius_km * direction_factor * fluctuation

        dlat, dlon = km_to_deg(adjusted_radius, lat)
        point_lat = lat + dlat * math.sin(angle_rad)
        point_lon = lon + dlon * math.cos(angle_rad)
        coords.append((point_lon, point_lat))

    coords.append(coords[0])
    return geojson.Polygon([coords])


def get_category(wind_speed):
    if wind_speed >= 157:
        return 5
    elif wind_speed >= 130:
        return 4
    elif wind_speed >= 111:
        return 3
    elif wind_speed >= 96:
        return 2
    elif wind_speed >= 74:
        return 1
    else:
        return 0


def compute_dynamic_radius(base_radius, wind_speed):
    return base_radius * (1 + max(0, (wind_speed - 25) / 100.0))


WIND_LEVELS = [
    {"level": "L5", "min": 74, "label": "Hurricane", "base_radius": 50},
    {"level": "L4", "min": 58, "label": "Strong TS", "base_radius": 100},
    {"level": "L3", "min": 39, "label": "Tropical Storm", "base_radius": 150},
    {"level": "L2", "min": 25, "label": "Depression", "base_radius": 200},
    {"level": "L1", "min": 0, "label": "Low Pressure", "base_radius": 250},
]


class MqttPublisher:
    def __init__(self, broker="localhost", port=1883, username=None, password=None):
        self.client = mqtt.Client()
        if username and password:
            self.client.username_pw_set(username, password)
        self.client.connect(broker, port)
        self.client.loop_start()

    def publish_polygon(self, level_id, geojson_feature):
        topic = f"producers/hurricane/data/{level_id}"
        message = {
            "action": "PUT",
            "geometry": geojson_feature["geometry"],
            "id": geojson_feature["id"],
            "properties": geojson_feature["properties"],
        }
        self.client.publish(topic, json.dumps(message))

    def publish_delete(self, level_id):
        topic = f"producers/hurricane/data/{level_id}"
        message = {
            "action": "DELETE",
            "id": level_id
        }
        self.client.publish(topic, json.dumps(message))

    def publish_clear(self):
        topic = f"producers/hurricane/control"
        message = {
            "action": "CLEAR"
        }
        self.client.publish(topic, json.dumps(message))

class Hurricane:
    def __init__(self, mqtt_publisher):
        self.lat = 15.0
        self.lon = -70.0
        self.wind_speed = 50.0
        self.pressure = 1005.0
        self.active_levels = set()
        self.mqtt_publisher = mqtt_publisher

    def update_position(self, t, total_steps):
        lat_start, lon_start = 15.0, -70.0
        lat_end, lon_end = 28.5, -80.0
        self.lat = lat_start + (lat_end - lat_start) * (t / total_steps)
        self.lon = lon_start + (lon_end - lon_start) * (t / total_steps)

    def fluctuate(self):
        self.wind_speed += random.uniform(-2.5, 3.5)
        self.wind_speed = max(0, self.wind_speed)
        base_pressure = 1010 - (self.wind_speed * 0.8)
        fluctuation = random.uniform(-2, 2)
        self.pressure = max(900, base_pressure + fluctuation)

    def generate_and_publish_features(self, timestamp):
        category = get_category(self.wind_speed)
        current_levels = set()

        print(f"[{timestamp}s] Wind: {self.wind_speed:.1f} mph, Cat {category}, Pos: ({self.lat:.2f}, {self.lon:.2f})")

        for level in WIND_LEVELS:
            if self.wind_speed >= level["min"]:
                radius_km = compute_dynamic_radius(level["base_radius"], self.wind_speed)
                polygon = create_asymmetric_wind_field(self.lat, self.lon, radius_km)
                feature = {
                    "type": "Feature",
                    "id": level["level"],
                    "geometry": polygon,
                    "properties": {
                        "wind_level": level["level"],
                        "label": level["label"],
                        "wind_speed_mph": round(self.wind_speed, 1),
                        "pressure_hPa": round(self.pressure, 1),
                        "category": category,
                        "radius_km": round(radius_km, 1),
                        "center_lat": self.lat,
                        "center_lon": self.lon,
                        "timestamp": timestamp,
                    },
                }
                current_levels.add(level["level"])
                self.mqtt_publisher.publish_polygon(level["level"], feature)

        for prev in self.active_levels:
            if prev not in current_levels:
                print(f"🛑 Wind level {prev} ceased at t={timestamp}s — sending DELETE")
                self.mqtt_publisher.publish_delete(prev)

        self.active_levels = current_levels


def main():
    parser = argparse.ArgumentParser(description="Hurricane Simulator")
    parser.add_argument("--interval", type=int, default=10, help="Update interval seconds")
    parser.add_argument("--duration", type=int, default=600, help="Simulation duration seconds")
    parser.add_argument("--broker", type=str, default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", type=str, default=None, help="MQTT username")
    parser.add_argument("--password", type=str, default=None, help="MQTT password")

    args = parser.parse_args()

    mqtt_pub = MqttPublisher(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
    )
    hurricane = Hurricane(mqtt_pub)

    total_steps = args.duration // args.interval

    print(f"🌪️  Starting hurricane simulation ({args.duration}s @ {args.interval}s intervals)...")
    mqtt_pub.publish_clear()

    for step in range(total_steps + 1):
        timestamp = step * args.interval
        hurricane.update_position(step, total_steps)
        hurricane.fluctuate()
        hurricane.generate_and_publish_features(timestamp)
        time.sleep(args.interval)

    print("✅ Simulation complete.")


if __name__ == "__main__":
    main()
