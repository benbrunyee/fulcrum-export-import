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
    {"id":"d67801a0-adc1-6f60-4b0d-ec3a7191b34b","geometry":{"type":"Point","coordinates":[-73.123456,42.123456]},"form_values": {"0129": "Hello world"}}
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
    t.List[RepeatableValue],
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


class AttachmentId(t.TypedDict):
    attachment_id: str


type AppElementTypes = t.Union[
    t.Literal["Section"],
    t.Literal["Repeatable"],
    t.Literal["TextField"],
    t.Literal["DateTimeField"],
    t.Literal["TimeField"],
    t.Literal["ChoiceField"],
    t.Literal["AddressField"],
    t.Literal["YesNoField"],
    t.Literal["AudioField"],
    t.Literal["PhotoField"],
    t.Literal["VideoField"],
]


class ChoiceValues(t.TypedDict):
    label: str
    value: str


class AppElement(t.TypedDict):
    data_name: str
    elements: t.Optional[t.List["AppElement"]]
    key: str
    label: str
    type: AppElementTypes
    allow_other: t.Optional[bool]
    choices: t.Optional[t.List[ChoiceValues]]
    multiple: t.Optional[bool]
    required: t.Optional[bool]
    required_conditions: t.Optional[t.List[t.Dict[str, t.Union[str, bool]]]]
    required_conditions_type: t.Optional[str]
    visible_conditions: t.Optional[t.List[t.Dict[str, t.Union[str, bool]]]]
    visible_conditions_behavior: t.Optional[str]
    visible_conditions_type: t.Optional[str]
    hidden: t.Optional[bool]
    max_length: t.Optional[int]
    min_length: t.Optional[int]
    numeric: t.Optional[bool]
    pattern: t.Optional[str]
    pattern_description: t.Optional[str]
    annotations_enabled: t.Optional[bool]
    deidentification_enabled: t.Optional[bool]
    display: t.Optional[str]
    geometry_required: t.Optional[bool]
    geometry_types: t.Optional[t.List[str]]
    timestamp_enabled: t.Optional[bool]
    track_enabled: t.Optional[bool]
    auto_populate: t.Optional[bool]
    negative: t.Optional[ChoiceValues]
    neutral: t.Optional[ChoiceValues]
    neutral_enabled: t.Optional[bool]
    positive: t.Optional[ChoiceValues]
    title_field_key: t.Optional[str]
    title_field_keys: t.Optional[t.List[str]]
    audio_enabled: t.Optional[bool]
    audio_notes: t.Optional[bool]


class App(t.TypedDict):
    """
    A Fulcrum app structure
    """

    assignment_enabled: bool
    attachment_ids: t.List[AttachmentId]
    auto_assign: bool
    bounding_box: t.List[float]
    created_at: str
    created_by: str
    created_by_id: str
    description: str
    elements: t.List[AppElement]
    field_effects: t.Optional[t.Any]
    form_links: t.Dict[str, t.List[t.Dict[str, str]]]
    geometry_required: bool
    geometry_types: t.List[str]
    hidden_on_dashboard: bool
    id: str
    image: str
    image_large: str
    image_small: str
    image_thumbnail: str
    name: str
    projects_enabled: bool
    record_changed_at: str
    record_count: int
    record_title_key: str
    report_templates: t.List[t.Any]
    script: str
    status_field: t.Dict[str, t.Any]
    system_type: t.Optional[str]
    title_field_keys: t.List[str]
    updated_at: str
    updated_by: str
    updated_by_id: str
    version: int
