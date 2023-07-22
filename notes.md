# After

New Survey App - Demo records (title)

- Q22222
- Bill Cooper, Q12740
- Bob, Q999999
- Seasick Steve, 0987654321 (x2)

Change

- "proximity_to_other_property_buildings" to "Proximity to buildings outside the site"
- "Close to water? (within 2 metres)" to "Close to a water body? (within 1 metre of the top of the bank)" (visibility logic to show next 3 fields below)

Add fields

- "EA spraying near water authorisation status"
  - "pending"
  - "approved"
- "Approval reference"
- "Approval expiry date"

- Feed the data in ‘EA…status’ to a new field in the Site Visits app, to appear as a direct copy (field name and data).

# Import/Export notes

- Added "Other" option to some fields so data is not lost

  - Property Type
  - Was Knotweed present on nearby property
  - ... (some others, name wasn't logged)

- There may be some clientele records with names that are very similar to existing clientele records

- Finding duplicates that aren't exactly is a time consuming task E.g., Finding matches between "Inlands Home", "Inlands Homes", "Inland's Home", etc...

- ec978219-2224-4d32-bb00-2e41326bdf9b: Both old and new values ("stand_location_visibly_impacted_areas") are populated. Old: 'front garden', New: 'front garden,front of property,side of property'

- Confirm "account_status" transformation
- Account status is in both site location and survey apps
  - Remove from site location
- Knotweed surveys have been split into their own records but the site visits link to a record, what conditions are used to determine what survey record should be used for the link?
  - Note of any records that have multiple surveys
  - Link to the most recent survey

# Repeatable Transformation Notes

## Generic

"pba_reference"/"account_reference" is a read-only field
"account_type" needs to be handled (choice list has changed - most likely for readability in the report/management plan)
same with "account_status"
document_status needs to be handled

"hide_title" and "hide_stand_number" are calculation fields
"stand_location" does not actually match the new stand location (different options available and a closer match is available "visibly_impacted_areas_subject_property")
"stand_location_visibly_impacted_areas" has the same choice list as "stand_location" but the field is hidden. Do we need this to be shown?
shouldn't the "proximity_to_other_property_buildings" field in new app should be a calculation field?

## KSMP

### SURVEY APP

- Create a field for "survey_findings_summary" just for the data

#### Value mismatches (choice list differences)

- document_status
- account_status
- open_space_area_approx
- primary_control_method
- treatment_programme_start_period
- other_activities_2
- surveyors_and_qualifications
- document_status
- account_status
- treatment_programme_start_period
- surveyors_and_qualifications
- document_status
- account_status
- growth_characteristics
- evidence_of_previous_treatment
- growth_characteristics
- site_photos_property
- contextual_photos
- break_before_site_plans
- contextual_photos
- site_photos_property
- contextual_photos
- break_before_site_plans
- site_photos_property
- contextual_photos
- site_photos_property
- stand_photos

## JKMR

### SURVEY APP

- Ignore "survey_plans" in base (knotweed survey repeatable). "site_plans" is the one we care about
- Some "client_names" fields are actually addresses
- Account status for client location does not have a match
- Client names need to be populated for all records
- "service_record_links" handle this field

#### Repeatable mappings

- knotweed_survey -> SURVEY APP

  1 record here is equivalent to 1 record for the new SURVEY APP.
  There are some records that have the same parent, this will need to be split into 2 records for the SURVEY APP (copy the parent info into each one).

- knotweed_survey_knotweed_stand_details -> Knotweed Stand Details
- site_plans -> break_before_site_plans
- site_photo_property -> site_photos_property
- knotweed_survey_knotweed_stand_details -> knotweed_stand_details
- knotweed_survey_knotweed_stand_details_stand_photos -> knotweed_stand_details_stand_photos
- spraying_near_water_documentation_aqherb01_if_appropriate -> ...
- knotweed_survey_survey_plans -> ...
- ... -> knotweed_stand_details_hide_stand_shape_and_area_capture_point_data

### SITE VISITS APP

- HERBICIDE APPLICATION & MONITORING RECORDS -> SITE VISITS
- OTHER TREATMENTS INC EXCAVATION -> SITE VISITS
- SITE MONITORING OBSERVATIONS AND RECOMMENDATIONS -> SITE VISITS

#### Value mismatches (choice list differences)

- account_type
- surveyors_and_qualifications
- condition_of_site
- record_type
- client_type
- plant_type
- job_type
- account_status
- was_knotweed_active_previously_on_the_site
- was_knotweed_present_on_a_nearby_property_previously
- validation
- other_invasive_weeds_identified_during_survey
- stand_location_site
- growth_characteristics
- evidence_of_previous_treatment
- type_of_water_body
- stand_location_other_property
- knotweed_is_growing_near_to_against_or_in
- stand_characteristics
- property_type
- distance_stand_to_other_buildingstructure_site_m
- site_photos_property
- break_before_site_plans
- contextual_photos
- stand_photos
- site_location
- is_knotweed_visibly_present_on_the_site
- is_knotweed_visibly_present_on_a_nearby_property

# Verification

## KSMP

- Q12231 /
- Q12129 /
- Q12426 /

### Notes

- Photo & Video captions need mapping manually

- "Can the survey proceed?" not populated
  - Determine source fields
- "Site-Specific Risk Assessment" not populated

  - Determine source fields

- Calculation fields don't get populated until you click edit and then re-save
- Client info will be populated once a re-link has occured (JKMR records)
- Stand details may require editing and saving for fields to be populated (JKMR records)

- "HERBICIDE APPLICATION & MONITORING RECORDS", "OTHER TREATMENTS INC EXCAVATION", "SITE MONITORING OBSERVATIONS AND RECOMMENDATIONS" not currently included in import
  - Map to "SITE VISIT RECORDS"

# Site Visit Notes

## JKMR

- "visit_category" = "Japanese Knotweed Management Record" for all JKMR records /
- "record_type_japanese_knotweed" = Repeatable name for site visit /
- "visit_type_japanese_knotweed_application_monitoring" = "visit_type" unless for Site Monitoring record then set value to "Scheduled Monitoring"? /
- "treatment_types" does not go with "treatment_types", it actually pairs with "visit_type_japanese_knotweed_other" /

- TODO: Populate the data from the "Survey" app via the link, check Sheets

## Existing SV

- A lot of survey record links are missing (the ID they are linked to do not point to any existing record meaning they have probably been deleted)
</s>

# IPMR Notes

## Process

### Mapping Process

1. Export existing SA + IPMR apps
1. Find differences
1. Duplicate SA app
1. Create new fields/restructure for IPMR fields
1. Export and find differences to ensure that all fields have been mapped to the new structure
1. Repeat for all relevant repeatable sections
1. Repeat for SV app

### Once all fields have been mapped to new app structure

Options

- Attempt to replicate structure in existing apps <-- This is the process that should be followed
  - Pros
    - Can be simple and quicker to do
  - Cons
    - Higher risk of data loss, an exact backup will need to be created with all records
- Export and import data via API
  - Pros
    - Can be more accurate and higher change capture rate
  - Cons
    - Can take a lot longer

## Survey Transformation

- Yearly schedules are different. IPMR = Jan/Feb, Mar/Apr whereas Survey app = Jan/Feb, Feb/Mar, Mar/Apr

- Knotweed Stand Details repeatable in the current SA is under a Knotweed Survey specific section.
  - We can pull out the stand details from the section and generalize it (have specific fields for knotweed)

- I will need to check whether any fields have been mapped to Knotweed specific fields (which will be hidden for this type of record)
  - Use [script](check_for_conditional_mapping.py)

- Changed "Target Plant(s)" from a single choice field to a multiple choice field

- Have a variable within field names that can be replaced with the plant name?
  - This will allow more fields to be generalized
  - Or we could generlize the field title anyways

- "spraying_near_water_documentation_aqherb01_if_appropriate" has been omitted (should this be the case?)
- "distance_from_stand_to_water_body" is under 2m then populate "close_to_water_within_2_metres" with "true"
- "does_site_to_be_surveyed_meet_generic_hs_criteria" same as "does_site_to_be_surveyed_meet_generic_rams_criteria"?

Fields to show for all plant types?

- other_impacted_site_details

TODO

- Map "is_the_entire_stand_located_within_the_boundaries_of_the_subject_site" to "stand_location_relative_to_boundaries"?
- Map "distance_from_stand_to_water_body" & "is_there_a_water_body_nearby" to "close_to_water_within_2_metres"?

### Changes Made

- App structure
- Report code
- Field prefix tags {BREAK} on "Site Plans"
- Calculation fields
  - Stand Title

## Site Visits Transformation

- "visit_type_invasive_plants_application" won't match up exactly but data will still be there and this can be edited manually in the future
- "adjuvant_included_in_mix" doesn't actually map to "adjuvant_included_in_mix" since data types are different

Questions

- SITE VISIT RECORDS - Why is there "Planned work carried out?" and "Treatment carried out?" fields? Aren't they the same? - Check notes
- SITE VISIT RECORDS - "Total number of knotweed stands identified" need to be conditionally hidden? - Check notes
- SITE VISIT RECORDS - "Technician feedback" should be within the "Service Visit Records" repeatable? - Check notes

## Import Process

1. Ensure that there are no more critical TODOS before proceeding with the merge (check Trello) : [/]
1. Create csv backups of the following apps and download them locally (csv, with photos, with GPS). Do each individually : []
    1. CLIENT                             : [/]
    1. SITE DETAILS                       : [/]
    1. SURVEY                             : []
    1. SITE VISIT RECORDS                 : []
    1. Invasive Plants Management Records : []
1. Export all data from Invasive Plants Management Records (csv, without photos) : []
1. Rename the following apps                                                     : []
    1. SURVEY -> SURVEY (LEGACY)                                                         : []
    1. Invasive Plants Management Records -> Invasive Plants Management Records (LEGACY) : []
1. (First time only) Add the status field to the new SURVEY app                                 : []
1. Duplicate the new SURVEY app and call it "SURVEY" using [duplicate_app.py](duplicate_app.py) : []
1. Confirm that the structure, status, title, title field matches fine                          : []
1. Ensure the logo and reports match the SURVEY (LEGACY) app                                    : []
1. Delete any testing apps                                                                      : []
    1. IMPORT apps : []
1. Export the CLIENT app (csv, without photos)                                                  : []
1. Using the CLIENT backup. Create new client records to upload                                 : []
1. Upload the new records to the existing CLIENT app                                            : []
1. Export the CLIENT app again                                                                  : []
1. Export the SITE DETAILS app (csv, without photos)                                            : []
1. Using the SITE DETAILS backup. Create new site details records                               : []
1. Upload the new records to the existing SITE DETAILS app                                      : []
1. Export the SITE DETAILS app again.                                                           : []
1. Using the predefined mappings                                                                : []
    1. Run all the following scripts: []
        1. [find_differences.py](find_differences.py) : []
        1. [transform.py](transform.py)               : []
        1. [import_api.py](import_api.py)             : []
    1. For these apps, in this order (run all the scripts for each app before proceeding to the next app): []
        1. IMPR (Invasive Plants Management Records)                  : []
        1. IPMR_SV (Invasive Plants Management Records - Site Visits) : []
        1. S (SURVEY - old to new)                                    : []
1. Confirm that all records have been uploaded                                                   : []
1. Do a splatter test across a minimum of 5 records to ensure that no problems can be identified : []
    1. Ensure field values are what is expected   : []
    1. Ensure that app links are set correctly    : []
    1. Ensure that record links are set correctly : []
