import random
from dataclasses import dataclass, field
from typing import Dict, List, Union

@dataclass
class PricingConfig:
    base_fare: Dict[str, float] = field(default_factory=lambda: {
        "min": 2.00,
        "max": 5.00,
        "default": 2.50
    })
    per_km_rate: Dict[str, float] = field(default_factory=lambda: {
        "min": 0.80,
        "max": 2.50,
        "default": 1.00
    })
    traffic_multiplier: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "low": 1.0,
        "moderate": [1.2, 1.4],
        "heavy": [1.5, 2.0]
    })
    demand_surge_pricing: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "low": 1.0,
        "moderate": [1.2, 1.5],
        "high": [1.6, 2.0],
        "extreme": [2.1, 3.0]
    })
    time_of_day_factor: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "off_peak": 1.0,
        "peak": [1.2, 1.5],
        "late_night": [1.3, 1.8]
    })
    weather_condition_factor: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "clear": 1.0,
        "light_rain": [1.1, 1.3],
        "heavy_rain": [1.5, 2.0],
        "snow_icy": [2.0, 3.0]
    })
    ride_type_factor: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "economy": 1.0,
        "premium": [1.5, 2.5],
        "luxury": [2.5, 4.0]
    })
    special_event_pricing: Dict[str, Union[float, List[float]]] = field(default_factory=lambda: {
        "normal": 1.0,
        "moderate": [1.2, 1.5],
        "high": [1.6, 2.5]
    })

def get_random_pricing_multipliers(config: PricingConfig) -> dict:
    """
    For each multiplier category in the pricing config, randomly pick a state and a corresponding multiplier.
    
    Returns:
        dict: A dictionary where each key is a multiplier field and its value is a dict:
              { "state": <chosen state>, "multiplier": <randomly selected multiplier> }
    """
    result = {}
    fields = [
        "traffic_multiplier",
        "demand_surge_pricing",
        "time_of_day_factor",
        "weather_condition_factor",
        "ride_type_factor",
        "special_event_pricing"
    ]
    for field_name in fields:
        field_dict = getattr(config, field_name)
        state_keys = list(field_dict.keys())
        chosen_state = random.choice(state_keys)
        value = field_dict[chosen_state]
        chosen_multiplier = random.choice(value) if isinstance(value, list) else value
        result[field_name] = {"state": chosen_state, "multiplier": chosen_multiplier}
    return result

# ----------------------
# Destructuring Example
# ----------------------
if __name__ == "__main__":
    pricing_config = PricingConfig()
    random_multipliers = get_random_pricing_multipliers(pricing_config)
    
    # Destructure a single field: traffic_multiplier
    traffic_info = random_multipliers.get("traffic_multiplier", {})
    traffic_state, traffic_multiplier = traffic_info.get("state"), traffic_info.get("multiplier")
    print("Traffic State:", traffic_state)
    print("Traffic Multiplier:", traffic_multiplier)
    
    # Destructure all fields at once:
    (traffic, surge, time_of_day, weather, ride, event) = (
        random_multipliers["traffic_multiplier"],
        random_multipliers["demand_surge_pricing"],
        random_multipliers["time_of_day_factor"],
        random_multipliers["weather_condition_factor"],
        random_multipliers["ride_type_factor"],
        random_multipliers["special_event_pricing"],
    )
    
    print("\nDestructured Multiplier Values:")
    print("Traffic:", traffic)
    print("Surge:", surge)
    print("Time of Day:", time_of_day)
    print("Weather:", weather)
    print("Ride:", ride)
    print("Event:", event)
