# How to use the Data Transformation Process

This document outlines the steps required to transform data and import it into various apps. The process includes exporting KMP records (with photos) and using several Python scripts to transform and import the data into Clientele, Site Locations, and SURVEY apps.

## Process Steps

1. Export KMP/JKMR records (including photos) and SURVEY app data.
   - Ensure that all repeatables in the SURVEY app contain at least 1 record otherwise the script will not be able to compare columns.
1. Update the arguments passed into `find_differences.py`, `create_clientele.py`, `create_site_locations.py` and `transform.py` via the `launch.json` file.
1. Run `create_clientele.py` to create a CSV file for the Clientele app.
1. Import the new CSV file into Clientele app.
1. Export Clientele app with the new records.
1. Update the argument path for the Clientele export in `create_site_locations.py` and run it to create a CSV file for the Site Locations app.
1. Import the new `site_locations.csv` file into Site Locations app.
1. Run `find_differences.py` to map mismatches to new columns.
   - (Optional) Delete the mappings directory found under `new_files\\{parent_directory}` (if it exists) if you don't want to use historical mappings.
1. Export Site Locations app with the new records.
1. Update the argument path for the Site Locations export in `transform.py` and run it to create a CSV file for the SURVEY app.
1. Move the `NEW_RECORDS.csv` file into the directory of the original export (where the photos are located).
1. Import the new records found in `NEW_RECORDS.csv` into the destination app.

## Import/Export Order

1. Export KMP.
1. Export SURVEY.
1. Import Clientele.
1. Export Clientele.
1. Import Site Locations.
1. Export Site Locations.
1. Import SURVEY.

## Explanation of New Files

### `client_names.csv`

This file contains a list of unique client names.

### `differences.csv`

This file lists the source columns that didn't have a direct match to the columns of the destination app layout. A closest match column is provided, and an updated column is used by the `transform.py` script to replace columns.

### `mappings.json`

This file contains a saved mapping of source columns to columns of the destination app layout. This file can be deleted to force the user to re-map the columns. Otherwise, this mapping is used on subsequent transformations (`transform.py`).

### `NEW_RECORDS.csv`

This file is an updated CSV ready for importing. It contains new records for the destination app and is the end result of this process.

### `site_locations.csv`

This file contains a list of site locations tied with Job IDs and Fulcrum IDs for the Client record link.

### `unmatched_columns.csv`

This file is a list of destination columns that have gone unmatched. These columns will contain no data when the `NEW_RECORDS.csv` is used for an import.

## Key

- JKMR = Japanese Knotweed Management Record
- SA = Survey App
- KMP = Knotweed Management Plan
- IPMR = Invasive Plants Management Record
- SV = Site Visits
