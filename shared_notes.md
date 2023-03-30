# Known Issues with Data Import

- Added "Other" option to some fields so data is not lost

  - Property Type
  - Was Knotweed present on nearby property
  - ... (some others, name wasn't logged)

- There may be some clientele records with names that are very similar to existing clientele records

  - Finding duplicates that aren't exactly is a time consuming task
  - E.g., Finding matches between "Inlands Home", "Inlands Homes", "Inland's Home", etc...

- When mapping old columns to new columns, aggregating data to allow for a direct field mapping, there has often been data in both the old and new columns, the new column data will be overritten

  - E.g., Both old and new values ("stand_location_visibly_impacted_areas") are populated. Old: 'front garden', New: 'front garden,front of property,side of property'

- There are plenty of choice list mismatches, the data still gets imported and displayed as previously.

- "Can the survey proceed?" not populated (editing the record will require you to add a value to these fields)
- "Site-Specific Risk Assessment" not populated but required fields (editing the record will require you to add a value to these fields)

- Calculation fields don't get populated until you click edit and then re-save
- Client info will be populated once a re-link has occured (JKMR records)
- Stand details may require editing and saving for fields to be populated (JKMR records)

- A lot of survey record links are missing (the ID they are linked to do not point to any existing record meaning they have probably been deleted or never existed in the first place). This doesn't affect the import
