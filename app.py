import streamlit as st
import csv
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from xml.etree import ElementTree as ET
import requests
from PIL import Image

im = Image.open("images/shift_square_icon.png")
st.set_page_config(
    page_title="Shift Planning",
    page_icon=im,
    layout="wide",
)

# Load the CSV file using the CSV module
csv_file = 'permitted.csv'  # Replace with the correct path to your CSV file
data = []

with open(csv_file, newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        data.append(row)

# Replace this with your actual Google Maps API Key
GOOGLE_API_KEY = st.secrets["GOOGLE_API"]

# Function to get the session URL for Google Maps tiles
def get_session_url(api_key):
    create_session_url = "https://tile.googleapis.com/v1/createSession"

    payload = {
        "mapType": "satellite",
        "language": "en-US",
        "region": "US",
    }

    headers = {'Content-Type': 'application/json'}

    response = requests.post(create_session_url,
                             json=payload,
                             headers=headers,
                             params={'key': api_key})

    if response.status_code == 200:
        session_token = response.json().get('session')
    else:
        st.error(f"Failed to create session: {response.text}")
        return None

    return ("https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}?session="
            + session_token
            + "&key="
            + api_key)

# Function to set up the Plotly map layout
def set_tile_layout(tile_url, lat, lon, zoom=17):
    return go.Layout(
        mapbox=dict(
            style="white-bg",
            layers=[{"below": 'traces',
                     "sourcetype": "raster",
                     "sourceattribution": "Google",
                     "source": [tile_url]}],
            center=dict(lat=lat, lon=lon),
            zoom=zoom),
        margin=dict(r=0, t=0, l=0, b=0),  # Remove margins
        showlegend=False  # Hide legend if any
    )

# Function to get the location coordinates from an address
def get_location(address):
    geolocator = Nominatim(user_agent="streamlit-app")
    location = geolocator.geocode(address)
    return location

# Function to parse KML file and extract polygon coordinates
def parse_kml(kml_file_path):
    tree = ET.parse(kml_file_path)
    root = tree.getroot()

    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
    coordinates = root.find('.//kml:coordinates', namespace).text.strip()
    
    # Split the coordinates into lat/lon pairs
    coord_pairs = coordinates.split()

    lons = []
    lats = []

    for pair in coord_pairs:
        lon, lat, _ = map(float, pair.split(','))
        lons.append(lon)
        lats.append(lat)

    return lats, lons

# Streamlit layout: Two columns
col1, col2 = st.columns([1, 1])

# Left Column: Search bar and map with full height
with col1:
    col1_1, col1_2 = st.columns([0.15, 0.85])
    with col1_1:
        st.image(
            "https://www.shift-construction.com/wp-content/uploads/2024/05/shift-blue-logo-white-text-120x72.png",
            use_column_width=True,
        )
    with col1_2:
        st.title("Permitted Development Search")
    
    # Full height container
    address = st.text_input("Enter an address:", key="search")

    if 'tiles_url' not in st.session_state:
        st.session_state.tiles_url = get_session_url(GOOGLE_API_KEY)

    if address and st.session_state.tiles_url:
        location = get_location(address)
        if location:
            # Save map center and zoom state
            if 'map_center' not in st.session_state:
                st.session_state.map_center = {"lat": location.latitude, "lon": location.longitude}
                st.session_state.zoom = 17.5  # Updated zoom level
            
            # Create the figure with the location and Google Maps tiles
            fig = go.Figure(layout=set_tile_layout(st.session_state.tiles_url,
                                                   st.session_state.map_center["lat"],
                                                   st.session_state.map_center["lon"],
                                                   st.session_state.zoom))

            # Add a marker for the searched address
            fig.add_trace(go.Scattermapbox(
                mode="markers",
                lat=[location.latitude],
                lon=[location.longitude],
                name='Location',
                marker=dict(size=10, color='red'),
                text=[location.address]
            ))

            # Track the selected option
            selected_option = st.session_state.get('selected_option', None)

            # Right Column: Simple table with checkboxes, thumbnails, titles, and descriptions
            if address and location:
                with col2:
                    st.header("Permitted Development Options", divider="orange")

                    # Create a table structure
                    for idx, row in enumerate(data):
                        col2_1, col2_2, col2_3, col2_4 = st.columns([0.05, 0.1, 0.2, 0.4])

                        # Determine if this checkbox should be checked
                        is_checked = selected_option == row['Permitted Development Options']

                        # Checkbox column
                        with col2_1:
                            checkbox = st.checkbox("", key=f"select_{idx}", value=is_checked)

                        # Thumbnail column
                        with col2_2:
                            st.image(f"images/{row['thumbnail']}", width=80)

                        # Title and description column
                        with col2_3:
                            st.write(f"**{row['Permitted Development Options']}**")

                        with col2_4:
                            st.write(row['Description'])

                        # If this checkbox is checked, update the selected option and clear other selections
                        if checkbox:
                            st.session_state['selected_option'] = row['Permitted Development Options']

                            # Load the corresponding KML file
                            lats, lons = parse_kml('kml/' + row['kml'])
                            fig.add_trace(go.Scattermapbox(
                                mode="lines",
                                fill="toself",
                                lat=lats,
                                lon=lons,
                                name=row['Permitted Development Options'],
                                line=dict(width=2, color='blue'),
                                fillcolor='rgba(0, 0, 255, 0.2)'
                            ))
                        elif selected_option == row['Permitted Development Options']:
                            # If unchecked, clear the selection
                            st.session_state['selected_option'] = None

            # Refresh the map to display the selected KML polygon
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
