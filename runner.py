import rasterio
import numpy as np
import requests
import json
from tqdm import tqdm
import winsound

# --- Load elevation data ---
elevation_dataset = rasterio.open("sudamerica.tif")
mosaic = elevation_dataset.read()
out_trans = elevation_dataset.transform

# --- Mask underwater (negative elevation) values ---
mosaic_masked = np.ma.masked_less(mosaic[0], -100)  # min in range is -67

# --- Define lat/lon limits ---
lat_lims = (-5, 2)
lon_lims = (-81.5, -74.9)

# --- Calculate row/col indices for slicing ---
row_start = int((out_trans.f - lat_lims[1]) / abs(out_trans.e))
row_end = int((out_trans.f - lat_lims[0]) / abs(out_trans.e))
col_start = int((lon_lims[0] - out_trans.c) / out_trans.a)
col_end = int((lon_lims[1] - out_trans.c) / out_trans.a)

# --- Slice the mosaic and mask to the specified lat/lon range ---
mosaic_masked_2 = mosaic_masked[row_start:row_end, col_start:col_end]


# --- Iterator for (lat, lon, elev) ---
def lats_longs():
    rows, cols = np.where(~mosaic_masked_2.mask)
    # Take every 2000th point for speed (adjust as needed)
    for r, c in zip(rows[::2000], cols[::2000]):
        lon = out_trans.c + out_trans.a * (c + col_start)
        lat = out_trans.f + out_trans.e * (r + row_start)
        elev = mosaic_masked_2[r, c]
        yield (lat, lon, elev)


# --- Function to get location info from API ---
def get_location_info(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    data = response.json()
    country = data.get("address", {}).get("country", "NA")
    state = data.get("address", {}).get("state", "NA")
    return data, country, state


# --- Main processing loop ---
results = []
for lat, lon, elev in tqdm(lats_longs(), desc="Processing points\n"):
    try:
        data, country, state = get_location_info(lat, lon)
    except Exception as e:
        print(f"Error fetching data for lat={lat}, lon={lon}: {e}")
        continue
    results.append(
        {
            "data": data,
            "lat": float(lat),
            "lon": float(lon),
            "country": country,
            "state": state,
            "elevation": float(elev),
        }
    )

# --- Save results ---
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# --- Beep when done ---
winsound.Beep(1000, 1000)
