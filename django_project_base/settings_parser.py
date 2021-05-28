from collections import Iterable
from typing import Any


def parse_settings(input_settings: tuple) -> None:
    from django.conf import settings
    for _setting in input_settings:
        setting_name: str = _setting['name']
        setting_default_value: Any = _setting["default"]
        setting_value: Any = getattr(_setting, _setting["name"], setting_default_value)
        if hasattr(settings, setting_name):
            _setting_existing_val: Any = getattr(settings, setting_name)
            if isinstance(_setting_existing_val, (tuple, list)):
                if isinstance(setting_value, Iterable):
                    _setting_existing_val: list = list(_setting_existing_val)
                    for v in setting_value:
                        _setting_existing_val.append(v)
                    _setting_existing_val: tuple = tuple(set(_setting_existing_val))
                else:
                    _setting_existing_val: list = list(_setting_existing_val)
                    _setting_existing_val.append(setting_value)
                    _setting_existing_val: tuple = tuple(set(_setting_existing_val))
                setattr(settings, setting_name, _setting_existing_val)
            else:
                pass
        else:
            setattr(settings, setting_name, setting_value)
