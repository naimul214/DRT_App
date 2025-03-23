import requests
from gtfs-realtime-bindings import gtfs_realtime_pb2
import gzip

# Define URLs
GTFS_REALTIME_URL = "https://drtonline.durhamregiontransit.com/gtfsrealtime/TripUpdates"

# Function to fetch GTFS Realtime data
def fetch_gtfs_realtime(url):
    response = requests.get(url)

    if response.status_code == 200:
        feed = gtfs_realtime_pb2.FeedMessage()  # Create a GTFS Realtime FeedMessage object
        feed.ParseFromString(response.content)  # Parse the Protobuf response

        # Print the first few trip updates
        for entity in feed.entity[:5]:  # Show only first 5 updates
            if entity.HasField("trip_update"):
                print("🚍 Trip ID:", entity.trip_update.trip.trip_id)
                print("📍 Route ID:", entity.trip_update.trip.route_id)
                for stop_time_update in entity.trip_update.stop_time_update:
                    print(f"   ⏱ Stop {stop_time_update.stop_id}: Arrival {stop_time_update.arrival.time}")

    else:
        print("❌ Failed to fetch GTFS Realtime data. Status code:", response.status_code)

# Run the function
fetch_gtfs_realtime(GTFS_REALTIME_URL)
