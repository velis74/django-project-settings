import logging
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string

from django_project_base.notifications.base.channels.integrations.provider_integration import ProviderIntegration
from django_project_base.notifications.base.phone_number_parser import PhoneNumberParser
from django_project_base.notifications.models import DeliveryReport, DjangoProjectBaseNotification
from django_project_base.utils import get_pk_name


class Recipient:
    identifier: str
    phone_number: str
    email: str
    unique_attribute: str

    def __init__(self, identifier: str, phone_number: str, email: str, unique_attribute: str = "identifier") -> None:
        super().__init__()
        self.identifier = identifier
        self.phone_number = (
            next(
                iter(
                    PhoneNumberParser.valid_phone_numbers([phone_number]) if phone_number and len(phone_number) else ""
                ),
                None,
            )
            or ""
        )
        self.email = email
        self.unique_attribute = unique_attribute

    def __eq__(self, __o: "Recipient") -> bool:
        return str(getattr(self, self.unique_attribute)) == str(getattr(__o, self.unique_attribute))

    def __hash__(self) -> int:
        return getattr(self, self.unique_attribute).__hash__()


class Channel(ABC):
    id = None

    name = ""

    notification_price = 0

    provider_setting_name = ""

    _provider: ProviderIntegration

    def _get_provider(self):
        return self._provider

    def _set_provider(self, val: ProviderIntegration):
        self._provider = val

    provider = property(_get_provider, _set_provider)

    def sender(self, notification: DjangoProjectBaseNotification) -> str:
        _sender = getattr(notification, "sender", {}).get(self.name)
        assert _sender, "Notification sender is required"
        return _sender

    def _find_provider(
        self, extra_settings: Optional[dict], setting_name: str, exclude: Optional[List[str]] = None
    ) -> Optional[ProviderIntegration]:
        def get_first_provider(val: Union[str, List]):
            if val and isinstance(val, list):
                return import_string(val[0])()

            return import_string(val)()

        if extra_settings and getattr(extra_settings.get("SETTINGS", object()), setting_name, None):
            return get_first_provider(getattr(extra_settings["SETTINGS"], setting_name))
        return get_first_provider(getattr(settings, setting_name, ""))

    def clean_recipients(self, recipients: List[Recipient]) -> List[Recipient]:
        return list(set(recipients))

    def create_delivery_report(
        self, notification: DjangoProjectBaseNotification, recipient: Union[Recipient, List[Recipient]], pk: str
    ) -> DeliveryReport:
        recs = recipient if isinstance(recipient, list) else [recipient]
        for user in recs:
            report = DeliveryReport.objects.create(
                notification=notification,
                user_id=user.identifier,
                channel=f"{self.__module__}.{self.__class__.__name__}",
                provider=f"{self.provider.__module__}.{self.provider.__class__.__name__}",
                pk=pk,
            )
            return report

    @abstractmethod
    def get_recipients(self, notification: DjangoProjectBaseNotification, unique_identifier="email") -> List[Recipient]:
        rec_obj = notification.recipients_list
        if not rec_obj:
            att = ("email", "phone_number", get_pk_name(get_user_model()))
            rec_obj = [
                {k: v for k, v in profile.__dict__.items() if not k.startswith("_") and k in att}
                for profile in [
                    get_user_model().objects.get(pk=u).userprofile for u in notification.recipients.split(",")
                ]
            ]
        return [
            Recipient(
                identifier=u.get("id", "") or "",
                email=u.get("email", "") or "",
                phone_number=u.get("phone_number", "") or "",
                unique_attribute=unique_identifier,
            )
            for u in rec_obj
        ]

    def send(self, notification: DjangoProjectBaseNotification, extra_data, **kwargs) -> int:
        logger = logging.getLogger("django")
        try:
            message = self.provider.get_message(notification)

            recipients = self.get_recipients(notification)

            if not recipients:
                raise ValueError("No valid recipients")

            exclude_providers: List[str] = []
            sent_no = 0

            def make_send(notification_obj, rec_obj, message_str) -> Optional[DeliveryReport]:
                dlr__uuid = str(uuid.uuid4())
                try:
                    self.provider.client_send(self.sender(notification_obj), rec_obj, message_str, dlr__uuid)
                    sent = True
                except Exception as te:
                    logger.exception(te)
                    sent = False
                try:
                    dlr = self.create_delivery_report(notification, recipient, dlr__uuid)
                    return dlr if sent else None
                except Exception as te:
                    logger.exception(te)
                    return None

            for recipient in recipients:  # noqa: E203
                try:
                    while (
                        dlr := make_send(
                            notification_obj=notification,
                            message_str=message,
                            rec_obj=recipient,
                        )
                    ) and dlr is None:
                        exclude_providers.append(str(self.provider.__module__))
                        next_provider = self._find_provider(
                            extra_settings=extra_data,
                            setting_name=self.provider_setting_name,
                            exclude=exclude_providers,
                        )
                        if next_provider:
                            self.provider = next_provider
                    if dlr:
                        self.provider.enqueue_dlr_request()
                        sent_no += 1
                except Exception as ge:
                    logger.exception(ge)

            if self.provider.is_sms_provider:
                from django_project_base.notifications.base.channels.integrations.t2 import SMSCounter

                sent_no = sent_no * SMSCounter.count(message)["messages"]
            return sent_no
        except Exception as e:
            logger.exception(e)
            raise e
