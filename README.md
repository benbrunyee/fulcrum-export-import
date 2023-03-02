# Process

1. Export KMP records (with photos) + SURVEY app
1. Update paths in [create_clientele.py](create_clientele.py),
[create_site_locations.py](create_site_locations.py), [find_differences.py](find_differences.py) & [transform.py](transform.py)
1. Run [create_clientele.py](create_clientele.py) to create a csv file for the Clientele app
1. Import to Clientele app with new records
1. Export Clientele app with new records
1. Update path to clientele export in [create_site_locations.py](create_site_locations.py) and run to create a csv file for the Site Locations app
1. Delete the mappings JSON file found under [new_files](new_files) if you don't want to use historical mappings (and if it exists)
1. Run [find_differences.py](find_differences.py) and map mismatches to new columns
1. Import to Site Locations with new records
1. Export Site Locations app with new records
1. Update path to site locations export in [transform.py](transform.py) and run to create a csv file for the SURVEY app
1. Import the new records found under [new_files](new_files)

# Import/Export order

1. Export KMP
1. Export SURVEY
1. Import Clientele
1. Export Clientele
1. Import Site Locations
1. Export Site Locations
1. Import SURVEY
