#STEP 9: Collect Additional Data
# scripts/district_info.py
"""
District and Resource Information for Jammu & Kashmir
Used for AI-powered Disaster Response System
Author: Nitesh Kumar
"""

# --- District-specific infrastructure and demographic data (Census 2011 + Estimated updates) ---
district_data = {
    "Jammu": {
        "coordinates": [32.73, 74.87],
        "population": 1529958,
        "area_sq_km": 2342,
        "hospitals": 8,
        "fire_stations": 5,
        "police_stations": 12,
        "vulnerable_areas": ["Tawi River Basin", "Ramnagar"],
        "road_connectivity": "High",
        "elevation": 327
    },
    "Srinagar": {
        "coordinates": [34.08, 74.80],
        "population": 1236829,
        "area_sq_km": 1979,
        "hospitals": 12,
        "fire_stations": 6,
        "police_stations": 18,
        "vulnerable_areas": ["Dal Lake", "Jhelum Banks", "Old City"],
        "road_connectivity": "High",
        "elevation": 1585
    },
    "Anantnag": {
        "coordinates": [33.73, 75.15],
        "population": 1078692,
        "area_sq_km": 3574,
        "hospitals": 4,
        "fire_stations": 2,
        "police_stations": 8,
        "vulnerable_areas": ["Lidder River", "Pahalgam"],
        "road_connectivity": "Medium",
        "elevation": 1601
    },
    "Baramulla": {
        "coordinates": [34.20, 74.34],
        "population": 1008039,
        "area_sq_km": 4243,
        "hospitals": 5,
        "fire_stations": 3,
        "police_stations": 10,
        "vulnerable_areas": ["Jhelum Valley", "Gulmarg"],
        "road_connectivity": "Medium",
        "elevation": 1590
    },
    "Kupwara": {
        "coordinates": [34.53, 74.26],
        "population": 870354,
        "area_sq_km": 2379,
        "hospitals": 3,
        "fire_stations": 2,
        "police_stations": 6,
        "vulnerable_areas": ["Lolab Valley", "Border Areas"],
        "road_connectivity": "Low",
        "elevation": 1640
    },
    "Pulwama": {
        "coordinates": [33.88, 74.92],
        "population": 560440,
        "area_sq_km": 1086,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 5,
        "vulnerable_areas": ["Shali River Tributaries", "Agricultural Plains"],
        "road_connectivity": "Medium",
        "elevation": 1630
    },
    "Budgam": {
        "coordinates": [34.02, 74.65],
        "population": 753745,
        "area_sq_km": 1361,
        "hospitals": 3,
        "fire_stations": 2,
        "police_stations": 6,
        "vulnerable_areas": ["Ferozepur Nallah", "Shallow Lakes"],
        "road_connectivity": "High",
        "elevation": 1614
    },
    "Bandipora": {
        "coordinates": [34.42, 74.64],
        "population": 392232,
        "area_sq_km": 345,
        "hospitals": 1,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Wular Lake Environs", "Gurez Valley"],
        "road_connectivity": "Low",
        "elevation": 1600
    },
    "Ganderbal": {
        "coordinates": [34.23, 75.10],
        "population": 297446,
        "area_sq_km": 259,
        "hospitals": 1,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Sind River Basin", "Kangan Road"],
        "road_connectivity": "Medium",
        "elevation": 1616
    },
    "Doda": {
        "coordinates": [33.15, 75.55],
        "population": 409936,
        "area_sq_km": 8912,
        "hospitals": 3,
        "fire_stations": 1,
        "police_stations": 5,
        "vulnerable_areas": ["Chenab River Banks", "Kishtwar-bound Roads"],
        "road_connectivity": "Medium",
        "elevation": 1107
    },
    "Kathua": {
        "coordinates": [32.37, 75.52],
        "population": 616435,
        "area_sq_km": 2502,
        "hospitals": 4,
        "fire_stations": 3,
        "police_stations": 7,
        "vulnerable_areas": ["Ravi River Plain", "Inter-state Border"],
        "road_connectivity": "High",
        "elevation": 390
    },
    "Udhampur": {
        "coordinates": [32.92, 75.13],
        "population": 554985,
        "area_sq_km": 2637,
        "hospitals": 3,
        "fire_stations": 2,
        "police_stations": 6,
        "vulnerable_areas": ["Hilly Terrain", "Highway Passes"],
        "road_connectivity": "Medium",
        "elevation": 756
    },
    "Rajouri": {
        "coordinates": [33.38, 74.31],
        "population": 642415,
        "area_sq_km": 2630,
        "hospitals": 3,
        "fire_stations": 2,
        "police_stations": 6,
        "vulnerable_areas": ["Azhikad Region", "LoC Proximity"],
        "road_connectivity": "Medium",
        "elevation": 915
    },
    "Poonch": {
        "coordinates": [33.77, 74.09],
        "population": 476835,
        "area_sq_km": 1674,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 5,
        "vulnerable_areas": ["Line of Control (LoC) Areas", "Jhelum Valley"],
        "road_connectivity": "Low",
        "elevation": 981
    },
    "Kulgam": {
        "coordinates": [33.65, 75.02],
        "population": 424483,
        "area_sq_km": 1067,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Veshaw River", "Qazigund Region"],
        "road_connectivity": "Medium",
        "elevation": 1700
    },
    "Kishtwar": {
        "coordinates": [33.31, 75.77],
        "population": 230696,
        "area_sq_km": 7737,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Chenab Basin", "Sinthan Pass"],
        "road_connectivity": "Low",
        "elevation": 1632
    },
    "Ramban": {
        "coordinates": [33.25, 75.25],
        "population": 283713,
        "area_sq_km": 1329,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Chenab Valley", "Landslide-prone Highways"],
        "road_connectivity": "Medium",
        "elevation": 1165
    },
    "Reasi": {
        "coordinates": [33.08, 74.83],
        "population": 314667,
        "area_sq_km": 1719,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Trikuta Hills", "Vaishno Devi Route"],
        "road_connectivity": "High",
        "elevation": 924
    },
    "Samba": {
        "coordinates": [32.57, 75.12],
        "population": 318611,
        "area_sq_km": 904,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Border Areas", "River Basins"],
        "road_connectivity": "High",
        "elevation": 384
    },
    "Shopian": {
        "coordinates": [33.71, 74.83],
        "population": 266215,
        "area_sq_km": 312,
        "hospitals": 1,
        "fire_stations": 1,
        "police_stations": 3,
        "vulnerable_areas": ["Rambi Ara Basin", "Zainapora Hills"],
        "road_connectivity": "Medium",
        "elevation": 2057
    },
    "Leh": {
        "coordinates": [34.15, 77.57],
        "population": 133487,
        "area_sq_km": 45110,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Indus Basin", "Nubra Valley"],
        "road_connectivity": "Low",
        "elevation": 3500
    },
    "Kargil": {
        "coordinates": [34.55, 76.13],
        "population": 140802,
        "area_sq_km": 14036,
        "hospitals": 2,
        "fire_stations": 1,
        "police_stations": 4,
        "vulnerable_areas": ["Suru Valley", "Zanskar Region"],
        "road_connectivity": "Low",
        "elevation": 2676
    }
}

# --- Centralized disaster response resources ---
available_resources = {
    "rescue_teams": [
        {"id": "NDRF_Jammu_1", "base": "Jammu", "capacity": 50, "equipment": ["boats", "medical", "rescue kits"]},
        {"id": "NDRF_Srinagar_1", "base": "Srinagar", "capacity": 45, "equipment": ["boats", "medical", "drones"]},
        {"id": "SDRF_Anantnag_1", "base": "Anantnag", "capacity": 30, "equipment": ["ropes", "stretchers"]},
        {"id": "NDRF_Udhampur_1", "base": "Udhampur", "capacity": 40, "equipment": ["heavy vehicles", "satcom"]},
        {"id": "Army_Heli_Unit", "base": "Leh", "capacity": 20, "equipment": ["helicopters", "medical support"]},
    ],
    "relief_supplies": {
        "food_packets": 15000,
        "water_kits": 30000,
        "blankets": 7000,
        "medical_kits": 2000,
        "tents": 800
    },
    "vehicles": [
        {"type": "ambulance", "count": 15, "base": "Jammu"},
        {"type": "ambulance", "count": 20, "base": "Srinagar"},
        {"type": "truck", "count": 10, "base": "Jammu"},
        {"type": "truck", "count": 8, "base": "Srinagar"},
        {"type": "helicopter", "count": 3, "base": "Leh"},
        {"type": "jeep", "count": 15, "base": "Udhampur"},
    ]
}

if __name__ == "__main__":
    print("✅ District and Resource Data Loaded Successfully!")
