from pathlib import Path
import time

import pandas as pd
import requests

from district_info import district_data


BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2020-01-01"
END_DATE = "2025-10-31"

OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "open_meteo"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_temperature_28_to_100cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_moisture_28_to_100cm",
]


EXCLUDED_DISTRICTS = {
    "Leh",
    "Kargil"
}


def download_district(district, info):

    latitude = info["coordinates"][0]
    longitude = info["coordinates"][1]

    output_file = OUTPUT_DIR / f"{district.lower()}.csv"

    # Skip if already downloaded
    if output_file.exists():
        print(f"\nSkipping {district} - already exists")
        return "skipped"

    print("\n" + "-" * 60)
    print(f"Downloading: {district}")
    print(f"Latitude: {latitude}")
    print(f"Longitude: {longitude}")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "auto",
    }

    max_retries = 5

    for attempt in range(1, max_retries + 1):

        try:

            print(f"Attempt {attempt}/{max_retries}")

            response = requests.get(
                BASE_URL,
                params=params,
                timeout=180
            )

            # Rate limit
            if response.status_code == 429:

                if attempt == max_retries:
                    raise Exception(
                        "Rate limit still active after maximum retries."
                    )

                wait_times = [60, 120, 180, 300]
                wait_time = wait_times[attempt - 1]

                print(
                    f"Rate limit (429). "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)
                continue

            response.raise_for_status()

            data = response.json()

            if "hourly" not in data:
                raise Exception(
                    "API response does not contain hourly data."
                )

            df = pd.DataFrame(data["hourly"])

            # Add district information
            df.insert(0, "district", district)
            df.insert(1, "latitude", latitude)
            df.insert(2, "longitude", longitude)

            df.to_csv(output_file, index=False)

            print(f"Saved: {output_file}")
            print(f"Rows: {len(df):,}")

            return "success"

        except requests.exceptions.Timeout:

            if attempt == max_retries:
                raise

            print("Request timed out.")
            print("Waiting 30 seconds before retry...")
            time.sleep(30)

        except requests.exceptions.RequestException as e:

            if attempt == max_retries:
                raise

            print(f"Request error: {e}")
            print("Waiting 30 seconds before retry...")
            time.sleep(30)

    return "failed"


def main():

    print("=" * 60)
    print("J&K HISTORICAL WEATHER DATA DOWNLOADER")
    print("=" * 60)

    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Output folder: {OUTPUT_DIR}")

    successful = []
    skipped = []
    failed = []

    for district, info in district_data.items():

        # Skip Ladakh
        if district in EXCLUDED_DISTRICTS:
            print(f"\nSkipping {district} - Ladakh")
            continue

        try:

            result = download_district(district, info)

            if result == "success":
                successful.append(district)

            elif result == "skipped":
                skipped.append(district)

            # Wait between districts
            print("\nWaiting 10 seconds before next district...")
            time.sleep(10)

        except Exception as e:

            print(f"\nERROR: {district}")
            print(e)

            failed.append(district)

            # Give API some recovery time
            print("Waiting 60 seconds before next district...")
            time.sleep(60)

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)

    print(f"New downloads: {len(successful)}")
    print(f"Already existed: {len(skipped)}")
    print(f"Failed: {len(failed)}")

    if successful:

        print("\nNewly downloaded:")

        for district in successful:
            print(f"- {district}")

    if skipped:

        print("\nAlready downloaded:")

        for district in skipped:
            print(f"- {district}")

    if failed:

        print("\nFailed districts:")

        for district in failed:
            print(f"- {district}")


if __name__ == "__main__":
    main()