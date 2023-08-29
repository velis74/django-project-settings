import logging

from django import db
from django.db import connections
from django.db.utils import load_backend
from django.utils import timezone

from django_project_base.notifications.base.enums import ChannelIdentifier
from django_project_base.notifications.models import DjangoProjectBaseNotification


class SendNotificationMixin(object):
    def make_send(self, notification: DjangoProjectBaseNotification, extra_data) -> DjangoProjectBaseNotification:
        sent_channels: list = []
        failed_channels: list = []
        exceptions = ""
        from django_project_base.licensing.logic import LogAccessService

        if notification.required_channels is None:
            return notification

        db_connection = "default"
        db_settings = extra_data.get("DATABASE")
        if db_settings:
            db_connection = f"notification-{notification.pk}"
            backend = load_backend(db_settings["SETTINGS"]["ENGINE"])
            dw = backend.DatabaseWrapper(db_settings["SETTINGS"])
            dw.connect()
            connections.databases[db_connection] = dw.settings_dict

        for channel_identifier in set(filter(lambda i: not (i is None), notification.required_channels.split(","))):
            channel = ChannelIdentifier.channel(channel_identifier)
            try:
                # check license
                LogAccessService().log(
                    user_profile_pk=notification.user,
                    notifications_channels_state=sent_channels,
                    record=notification,
                    item_price=channel.notification_price,
                    comment=str(channel),
                    on_sucess=lambda: channel.send(notification, extra_data),
                    db=db_connection,
                    settings=extra_data.get("SETTINGS", object()),
                )
                sent_channels.append(channel)
            except Exception as e:
                logging.getLogger(__name__).error(e)
                failed_channels.append(channel)
                exceptions += f"{str(e)}\n\n"

        if notification.created_at:
            notification.sent_channels = (
                ",".join(
                    list(
                        map(
                            lambda f: str(f),
                            filter(
                                lambda d: d is not None,
                                map(lambda c: c.name, sent_channels),
                            ),
                        )
                    )
                )
                if sent_channels
                else None
            )
            notification.failed_channels = (
                ",".join(
                    list(
                        map(
                            lambda f: str(f),
                            filter(
                                lambda d: d is not None,
                                map(lambda c: c.name, failed_channels),
                            ),
                        )
                    )
                )
                if failed_channels
                else None
            )
            notification.sent_at = timezone.now().timestamp()
            notification.exceptions = exceptions if exceptions else None

            notification.save(
                update_fields=[
                    "sent_at",
                    "sent_channels",
                    "failed_channels",
                    "exceptions",
                ],
                using=db_connection,
            )

            if db_settings:
                db.connections.close_all()
        return notification
