from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")
test = "서울 마포구 도화동 205-6"
# 주소로부터 위도와 경도 얻기
location = geolocator.geocode(test)
if location:
    latitude = location.latitude
    longitude = location.longitude
    print(f"Latitude: {latitude}, Longitude: {longitude}")
else:
    print("Geocoding failed")
