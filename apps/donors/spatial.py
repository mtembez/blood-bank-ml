import math
from decimal import Decimal
from django.db import connection
from apps.donors.models import Donor


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in kilometers."""
    R = 6371.0088  # Earth mean radius in kilometers
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def find_nearby_donors(
    latitude: float,
    longitude: float,
    radius_km: float = 25.0,
    blood_group: str = None,
    eligible_only: bool = True,
):
    """Query donors within a given radius (km) using PostGIS spatial SQL or Haversine fallback.

    Annotates each donor with calculated 'distance_km' and orders by proximity.
    """
    lat = float(latitude)
    lon = float(longitude)
    radius = float(radius_km)

    # 1. Base query filter
    qs = Donor.objects.all()
    if eligible_only:
        qs = qs.filter(is_eligible=True)
    if blood_group:
        qs = qs.filter(blood_group=blood_group)

    # 2. Check if PostGIS extension is available in current database
    has_postgis = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis';")
            has_postgis = cursor.fetchone() is not None
    except Exception:
        has_postgis = False

    if has_postgis:
        # High-performance PostGIS geography spatial query
        radius_meters = radius * 1000.0
        sql = f"""
            SELECT id,
                   ST_Distance(
                       ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                       ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography
                   ) / 1000.0 AS distance_km
            FROM donors
            WHERE ST_DWithin(
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography,
                {radius_meters}
            )
            ORDER BY distance_km ASC;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

            dist_map = {row[0]: round(float(row[1]), 2) for row in rows}
            donors = list(qs.filter(id__in=dist_map.keys()))
            for d in donors:
                d.distance_km = dist_map.get(d.id, 0.0)
            donors.sort(key=lambda x: getattr(x, "distance_km", 0.0))
            return donors
        except Exception:
            # Fall back to Haversine on any PostGIS query exception
            pass

    # 3. Deterministic Haversine Fallback Engine (with bounding box pre-filter)
    # 1 degree latitude ~ 111 km
    lat_delta = radius / 111.0
    # 1 degree longitude ~ 111 * cos(lat)
    lon_delta = radius / (111.0 * math.cos(math.radians(lat)) + 1e-6)

    candidates = qs.filter(
        latitude__gte=Decimal(str(lat - lat_delta)),
        latitude__lte=Decimal(str(lat + lat_delta)),
        longitude__gte=Decimal(str(lon - lon_delta)),
        longitude__lte=Decimal(str(lon + lon_delta)),
    )

    results = []
    for donor in candidates:
        dist = haversine_distance_km(lat, lon, donor.latitude, donor.longitude)
        if dist <= radius:
            donor.distance_km = round(dist, 2)
            results.append(donor)

    results.sort(key=lambda x: x.distance_km)
    return results
