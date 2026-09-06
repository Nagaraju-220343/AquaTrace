import pytest
from app.modules.geotagging.geotagger import calculate_geotag

def test_missing_metadata():
    bbox = [100, 100, 200, 200]
    result = calculate_geotag(bbox, None)
    
    assert result["geo_status"] == "UNAVAILABLE"
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert result["dimensions_meters"] is None

def test_approximate_metadata():
    bbox = [100, 100, 200, 200]
    # No meters_per_pixel provided
    metadata = {
        "origin_lat": 40.0,
        "origin_lon": -70.0,
        "heading": 0.0
    }
    
    result = calculate_geotag(bbox, metadata)
    
    assert result["geo_status"] == "APPROXIMATE"
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    
def test_valid_metadata():
    bbox = [0, 0, 100, 100]
    metadata = {
        "origin_lat": 40.0,
        "origin_lon": -70.0,
        "heading": 90.0, # East
        "meters_per_pixel": 1.0,
        "origin_x": 0.0,
        "origin_y": 0.0
    }
    
    # Center of bbox is 50, 50.
    # dx = 50, dy = 50.
    # At heading 90, +Y is East, +X is South (relative to heading).
    result = calculate_geotag(bbox, metadata)
    
    assert result["geo_status"] == "VALID"
    # Dimensions should be 100 * 1.0 = 100m
    assert result["dimensions_meters"] == [100.0, 100.0]
    assert result["uncertainty_meters"] == 2.0
    
    # Should move slightly from origin
    assert result["latitude"] != 40.0
    assert result["longitude"] != -70.0
