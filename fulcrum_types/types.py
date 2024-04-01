import typing as t


class DictValue(t.TypedDict):
    choice_values: t.List[str]
    other_values: t.List[str]


class PhotoValue(t.TypedDict):
    photo_id: str
    caption: str


class VideoValue(t.TypedDict):
    video_id: str
    caption: str


class AudioValue(t.TypedDict):
    audio_id: str
    caption: str


class SignatureValue(t.TypedDict):
    timestamp: str
    signature_id: str


class RecordLinkValue(t.TypedDict):
    record_id: str


class AddressValue(t.TypedDict):
    sub_admin_area: str
    locality: str
    admin_area: str
    postal_code: str
    country: str
    suite: str
    sub_thoroughfare: str
    thoroughfare: str


type FormValuesWithoutRepeatableValue = t.Union[
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
{'id': 'd11529d5-3385-a7c4-c402-f0b87e6cef27', 'geometry': {'type': 'Point', 'coordinates': [...]}, 'form_values': {'2227': 'Small amount of Japanese knotweed crown and rhizome removed from impacted area on both sides of fence. Removed materials placed on south side of fence behind shrubs.', '4bed': '2016-03-16', 'd7ff': '12:00', '16cd': {...}, 'e37d': {...}, '2c87': {...}, '7e0f': None, '8f6d': 'yes', '35fb': [...], '54ec': None, '4a2e': None, 'c4b3': 'yes'}, 'dirty': True, 'updated_at': '1458221440', 'created_at': '1458221440', 'version': 2, 'created_by_id': '0181c4b5-662b-474a-bba8-1a1c1af8374d', 'updated_by_id': '4aff9341-7d7e-4783-a902-601f9a73ac96', 'changeset_id': '6d64a2fa-ec74-498a-b3c8-6e0a1482d228', 'created_duration': None, 'updated_duration': None, 'edited_duration': None}
"""


class RepeatableValue(t.TypedDict):
    """
    [{"id":"d67801a0-adc1-6f60-4b0d-ec3a7191b34b","geometry":{"type":"Point","coordinates":[-73.123456,42.123456]},"form_values": {"0129": "Hello world"}}]
    """

    id: str
    geometry: t.Dict[str, t.Any]
    form_values: "FormValue"
    created_at: str
    updated_at: str
    version: int
    created_by_id: str
    updated_by_id: str
    changeset_id: str
    created_duration: t.Optional[str]
    updated_duration: t.Optional[str]
    edited_duration: t.Optional[str]


type FormValues = t.Union[
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

type FormValue = t.Union[t.Dict[str, FormValues], t.TypeAlias["FormValue"]]


class VisibleCondition(t.TypedDict):
    field_key: str
    operator: t.Literal["equal_to", "not_equal_to", "is_not_empty"]
    value: str


class AppElement(t.TypedDict):
    key: str
    data_name: str
    visible_conditions_type: t.Literal["all", "any"]
    visible_conditions: t.List[VisibleCondition]


class Record(t.TypedDict):
    """
    https://docs.fulcrumapp.com/reference/records-intro#form-value-field-types
    """

    form_id: str
    latitude: float
    longitude: float
    form_values: FormValue
    status: str
    version: int
    id: str
    created_at: str
    updated_at: str
    client_created_at: str
    client_updated_at: str
    created_by: str
    created_by_id: str
    updated_by: str
    updated_by_id: str
    changeset_id: str
    project_id: str
    assigned_to: str
    assigned_to_id: str
    created_duration: int
    updated_duration: int
    edited_duration: int
    created_location: t.Dict[str, float]
    updated_location: t.Dict[str, float]
    altitude: float
    speed: float
    course: float
    horizontal_accuracy: float
    vertical_accuracy: float
    geometry: t.Any
