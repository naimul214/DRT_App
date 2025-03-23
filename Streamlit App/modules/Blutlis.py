import requests
import pandas as pd
import streamlit as st
from modules.DataPrep import Routes, Towards  # Import the preprocessed DataFrames
from google.transit import gtfs_realtime_pb2

GTFS_URL = "https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions"

# Load Routes Data
@st.cache_data
def load_routes():
    return Routes  # Directly return the DataFrame

# Load Directions Data
@st.cache_data
def load_directions():
    return Towards  # Directly return the DataFrame

# Fetch Vehicles Data
@st.cache_data(ttl=60)
def fetch_vehicles_data():
    try:
        response = requests.get(GTFS_URL)
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        vehicles = []
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                vehicle = entity.vehicle
                vehicles.append({
                    "id": vehicle.vehicle.id,
                    "route_id": vehicle.trip.route_id,
                    "latitude": vehicle.position.latitude,
                    "longitude": vehicle.position.longitude,
                    "speed": vehicle.position.speed if vehicle.position.HasField("speed") else None,
                    "timestamp": vehicle.timestamp
                })
        
        return pd.DataFrame(vehicles)
    except requests.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

# Filter Vehicles Data by 'concat' (route_id + direction_id)
def fetch_buses_by_route_direction(concat):
    data = fetch_vehicles_data()
    
    if data is None:
        return pd.DataFrame()
    
    buses = []
    
    for _, vehicle in data.iterrows():
        route_id = vehicle["route_id"]
        direction_id = vehicle["direction_id"]
        combined_id = str(route_id) + str(direction_id)

        if combined_id == concat:
            buses.append({
                "trip_id": vehicle.get("trip_id"),
                "route_id": route_id,
                "direction_id": direction_id,
                "vehicle_id": vehicle.get("id"),
                "start_time": vehicle.get("start_time"),
                "start_date": vehicle.get("start_date"),
                "latitude": vehicle.get("latitude"),
                "longitude": vehicle.get("longitude"),
                "timestamp": vehicle.get("timestamp")
            })

    return pd.DataFrame(buses)