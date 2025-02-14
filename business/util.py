from dataclasses import dataclass, field
import random
from typing import Union, List, Dict
from decimal import Decimal, ROUND_HALF_UP

from business.models import Trip

# ==============================
# Pricing Configuration Object
# ==============================

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


def calculate_trip_fare(
    trip: Trip,
    config: PricingConfig,
    traffic_key: str = "low",
    surge_key: str = "low",
    time_of_day_key: str = "off_peak"
) -> (Decimal, dict):
    """
    Calculate the total fare for a Trip instance using the PricingConfig object.
    The multipliers are selected via keys.

    Parameters:
        trip (Trip): The Trip instance.
        config (PricingConfig): The pricing configuration object.
        traffic_key (str): Key for traffic multiplier (e.g., "low", "moderate", "heavy").
        surge_key (str): Key for surge multiplier (e.g., "low", "moderate", "high", "extreme").
        time_of_day_key (str): Key for time of day factor (e.g., "off_peak", "peak", "late_night").

    Returns:
        A tuple containing:
            - total_fare (Decimal): The calculated total fare.
            - fare_breakdown (dict): A detailed breakdown of fare components.
    """
    # Retrieve default pricing parameters
    base_fare = config.base_fare.get("default", 2.50)
    per_km_rate = config.per_km_rate.get("default", 1.00)
    distance = trip.distance

    # Helper to extract a multiplier value (if list, use the first element)
    def get_multiplier(value: Union[float, List[float]]) -> float:
        if isinstance(value, list):
            return value[0]
        return value

    # Get multipliers from the config using the provided keys
    traffic_multiplier = get_multiplier(config.traffic_multiplier.get(traffic_key, 1.0))
    surge_multiplier = get_multiplier(config.demand_surge_pricing.get(surge_key, 1.0))
    time_of_day_multiplier = get_multiplier(config.time_of_day_factor.get(time_of_day_key, 1.0))

    # Combine multipliers
    combined_multiplier = traffic_multiplier * surge_multiplier * time_of_day_multiplier

    # Calculate fare: (base fare + distance * per km rate) * combined multiplier
    raw_fare = (base_fare + (distance * per_km_rate)) * combined_multiplier
    total_fare = Decimal(raw_fare).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Build a detailed breakdown
    fare_breakdown = {
        "base_fare": base_fare,
        "per_km_rate": per_km_rate,
        "distance": distance,
        "traffic_multiplier": traffic_multiplier,
        "surge_multiplier": surge_multiplier,
        "time_of_day_multiplier": time_of_day_multiplier,
        "combined_multiplier": combined_multiplier,
        "calculated_fare": float(total_fare)
    }

    # Update the Trip instance
    trip.fare_breakdown = fare_breakdown
    trip.total_fare = total_fare
    trip.save()

    return total_fare, fare_breakdown


def get_random_pricing_multipliers(config: PricingConfig) -> dict:
    """
    For each multiplier category in the pricing config, randomly pick a state and a corresponding multiplier.
    
    Returns:
        dict: A dictionary with keys corresponding to each multiplier field and values being a dict:
              {
                  "state": <selected state key>,
                  "multiplier": <randomly selected multiplier>
              }
    """
    result = {}
    # List of multiplier fields to process
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
        # Randomly select one of the states
        state_keys = list(field_dict.keys())
        chosen_state = random.choice(state_keys)
        value = field_dict[chosen_state]
        # If value is a list (range), pick a random value from it; otherwise, use the fixed float.
        if isinstance(value, list):
            chosen_multiplier = random.choice(value)
        else:
            chosen_multiplier = value
        result[field_name] = {"state": chosen_state, "multiplier": chosen_multiplier}
    return result