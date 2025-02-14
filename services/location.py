from geopy.geocoders import Nominatim
from geopy.distance import geodesic

class LocationService:
    def __init__(self, user_agent="location_service"):
        self.geolocator = Nominatim(user_agent=user_agent)

    def get_coordinates(self, location_name):
        """Returns the latitude and longitude of a given location name."""
        location = self.geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None

    def get_location_name(self, latitude, longitude):
        """Returns the location name from given latitude and longitude."""
        location = self.geolocator.reverse((latitude, longitude), language='en', exactly_one=True)
        if location:
            return location.address
        else:
            return None

    def calculate_distance(self, loc1, loc2, by_name=True):
        """
        Determines the distance between two locations.
        - If by_name is True, loc1 and loc2 should be location names.
        - Otherwise, loc1 and loc2 should be tuples of (latitude, longitude).
        """
        if by_name:
            coords1 = self.get_coordinates(loc1)
            coords2 = self.get_coordinates(loc2)
        else:
            coords1, coords2 = loc1, loc2

        if coords1 and coords2:
            return geodesic(coords1, coords2).kilometers
        else:
            return None

    def search_places(self, query, limit=10):
        """Searches for places matching the query and returns their details."""
        results = self.geolocator.geocode(query, exactly_one=False)
        if results:
            places = []
            for result in results[:limit]:
                place = {
                    'name': result.address,
                    'latitude': result.latitude,
                    'longitude': result.longitude
                }
                places.append(place)
            return places
        else:
            return None


# Example Usage
if __name__ == "__main__":
    service = LocationService()

    import time
    
    # places = [
    #     "Gbagada", "Shomolu", "Akoka", "Abule Oja", "Abule Ijesha", "Surulere", "Yaba",
    #     "Bariga", "Ilupeju", "Fadeyi", "Igbobi", "Abule Okuta", "Onipan", "Iwaya", 
    #     "Onike", "Idi Araba", "Idi Oro"
    # ]
    
    # for place in places:
    #     coords = service.get_coordinates(place)
    #     print(f"{place}: {coords}")
    #     time.sleep(1)  # Wait for 1 second between requests



    # Get coordinates of a location
    coords = service.get_coordinates("New York")
    print(f"Coordinates of New York: {coords}")

    # Get location name from coordinates
    location_name = service.get_location_name(40.7128, -74.0060)
    print(f"Location name: {location_name}")

    loc_1 = "University of Lagos"
    loc_2 = "Bariga"

    # Calculate distance between two locations
    distance = service.calculate_distance(loc_1, loc_2)
    print(f"Distance between {loc_1} and {loc_2}: {distance:.2f} km")

    # # Search for multiple results for a location name
    # places = service.search_places("Bariga")
    # if places:
    #     for idx, place in enumerate(places, start=1):
    #         print(f"{idx}. {place['name']} (Latitude: {place['latitude']}, Longitude: {place['longitude']})")
    # else:
    #     print("No results found.")

