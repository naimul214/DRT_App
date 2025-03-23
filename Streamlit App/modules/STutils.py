import pytz
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from modules.DataPrep import Routes, Towards, StopMapLocation, StopTimesPerTrip
from google.transit import gtfs_realtime_pb2

# API Endpoint
GTFSR_API_URL = "https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions"

# Load Routes Data
@st.cache_data
def load_routes():
    return Routes  # Directly returning the DataFrame from DataPrep.py

# Load Directions Data
@st.cache_data
def load_directions(route_id):
    return Towards[Towards["route_id"] == route_id]

# Load Stops Data filtered by trip_id
@st.cache_data
def load_stops(trip_id):
    filtered_stops = StopMapLocation[StopMapLocation["trip_id"] == trip_id].copy()
    filtered_stops["stop_full"] = filtered_stops["stop_code"].astype(str) + " - " + filtered_stops["stop_name"]
    return filtered_stops

# Fetch GTFSR Data from API
@st.cache_data(ttl=60)
def fetch_gtfsr_data():
    try:
        response = requests.get(GTFSR_API_URL)
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
                    "direction_id": vehicle.trip.direction_id,
                    "latitude": vehicle.position.latitude,
                    "longitude": vehicle.position.longitude,
                    "speed": vehicle.position.speed if vehicle.position.HasField("speed") else None,
                    "timestamp": vehicle.timestamp
                })
        
        return pd.DataFrame(vehicles)
    except requests.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

# Process and Filter GTFSR Data
def process_gtfsr_data(data, concat):
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

# Load Stop Times Per Trip Data
@st.cache_data
def load_stop_times_per_trip():
    return StopTimesPerTrip  # Directly return the DataFrame

# Calculate Minutes Left
def calculate_minutes_left(arrival_time):
    current_time = datetime.now().time()
    arrival_datetime = datetime.combine(datetime.today(), arrival_time)
    delta = arrival_datetime - datetime.combine(datetime.today(), current_time)
    return int(delta.total_seconds() // 60)

# Convert 'arrival_time' to datetime for comparison, handling times beyond 23:59:59
def convert_gtfs_time(time_str):
    """Converts GTFS times (which can exceed 24:00:00) to valid datetime.time."""
    try:
        # Split the time string
        h, m, s = map(int, time_str.split(':'))
        
        # Normalize times greater than 24:00:00
        if h >= 24:
            h = h - 24
            return (datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=h, minutes=m, seconds=s) + timedelta(days=1)).time()
        else:
            return datetime.strptime(time_str, "%H:%M:%S").time()
    except:
        return None  # Handle unexpected formats

# Updated get_upcoming_buses function
def get_upcoming_buses(route_id, direction_id, selected_stop):
    # Fetch live trip data from the API
    gtfsr_data = fetch_gtfsr_data()

    if not gtfsr_data:
        st.error("❌ No data fetched from the API.")
        return pd.DataFrame()

    concat = str(route_id) + str(direction_id)
    scheduled_time = process_gtfsr_data(gtfsr_data, concat)

    if scheduled_time.empty:
        st.warning("⚠️ No scheduled trips found for this route and direction.")
        return pd.DataFrame()

    # Get distinct trip_ids
    unique_trip_ids_df = scheduled_time[['trip_id']].drop_duplicates()

    # Load StopTimesPerTrip.txt
    stop_times_df = load_stop_times_per_trip()

    # Filter StopTimesPerTrip by trip_id and stop_id
    filtered_stpr_df = stop_times_df[
        (stop_times_df['trip_id'].isin(unique_trip_ids_df['trip_id'])) &
        (stop_times_df['stop_id'] == selected_stop)
    ]

    if filtered_stpr_df.empty:
        st.warning("⚠️ No upcoming buses for this stop.")
        return pd.DataFrame()

    # Apply the custom converter to handle '24:' times
    filtered_stpr_df.loc[:, 'arrival_time'] = filtered_stpr_df['arrival_time'].apply(convert_gtfs_time)

    # Filter out past buses
    current_time = datetime.now().time()
    upcoming_buses_df = filtered_stpr_df[filtered_stpr_df['arrival_time'] > current_time].copy()

    # Calculate minutes left
    upcoming_buses_df['minutes_left'] = upcoming_buses_df['arrival_time'].apply(calculate_minutes_left)

    # Select relevant columns
    upcoming_buses_df = upcoming_buses_df[['trip_id', 'minutes_left']].copy()

    return upcoming_buses_df.sort_values(by="minutes_left")

