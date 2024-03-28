import typing as t

DictValue = t.TypedDict(
    "DictValue", {"choice_values": t.List[str], "other_values": t.List[str]}
)
PhotoValue = t.TypedDict(
    "PhotoValue",
    {
        "photo_id": str,
        "caption": str,
    },
)
VideoValue = t.TypedDict(
    "VideoValue",
    {
        "video_id": str,
        "caption": str,
    },
)
AudioValue = t.TypedDict(
    "AudioValue",
    {
        "audio_id": str,
        "caption": str,
    },
)
SignatureValue = t.TypedDict(
    "SignatureValue",
    {
        "timestamp": str,
        "signature_id": str,
    },
)
RecordLinkValue = t.List[t.TypedDict("RecordLinkValue", {"record_id": str})]
AddressValue = t.TypedDict(
    "AddressValue",
    {
        "sub_admin_area": str,
        "locality": str,
        "admin_area": str,
        "postal_code": str,
        "country": str,
        "suite": str,
        "sub_thoroughfare": str,
        "thoroughfare": str,
    },
)
FormValuesWithoutRepeatableValue = t.Union[
    str,
    DictValue,
    PhotoValue,
    AddressValue,
    RecordLinkValue,
    SignatureValue,
    AudioValue,
    VideoValue,
]
"""
[{"id":"d67801a0-adc1-6f60-4b0d-ec3a7191b34b","geometry":{"type":"Point","coordinates":[-73.123456,42.123456]},"form_values": {"0129": "Hello world"}}]
"""
RepeatableValue = t.TypedDict(
    "RepeatableValue",
    {
        "id": str,
        "geometry": t.Dict[str, t.Any],
        "form_values": t.Dict[
            str,
            t.Union[
                FormValuesWithoutRepeatableValue,
                "RepeatableValue",
            ],
        ],
    },
)
FormValues = t.Union[
    str,
    DictValue,
    PhotoValue,
    AddressValue,
    RecordLinkValue,
    SignatureValue,
    AudioValue,
    VideoValue,
    RepeatableValue,
]

VisibleCondition = t.TypedDict(
    "VisibleCondition",
    {
        "field_key": str,
        "operator": t.Literal["equal_to", "not_equal_to", "is_not_empty"],
        "value": str,
    },
)

AppElement = t.TypedDict(
    "AppElement",
    {
        "key": str,
        "data_name": str,
        "visible_conditions_type": t.Literal["all", "any"],
        "visible_conditions": t.List[VisibleCondition],
    },
)

# https://docs.fulcrumapp.com/reference/records-intro#form-value-field-types
Record = t.TypedDict(
    "Record",
    {
        "form_id": str,
        "latitude": float,
        "longitude": float,
        "form_values": t.Dict[str, FormValues],
        "status": str,
        "version": int,
        "id": str,
        "created_at": str,
        "updated_at": str,
        "client_created_at": str,
        "client_updated_at": str,
        "created_by": str,
        "created_by_id": str,
        "updated_by": str,
        "updated_by_id": str,
        "changeset_id": str,
        "project_id": str,
        "assigned_to": str,
        "assigned_to_id": str,
        "created_duration": int,
        "updated_duration": int,
        "edited_duration": int,
        "created_location": t.Dict[str, float],
        "updated_location": t.Dict[str, float],
        "altitude": float,
        "speed": float,
        "course": float,
        "horizontal_accuracy": float,
        "vertical_accuracy": float,
        "geometry": t.Any,
    },
)
