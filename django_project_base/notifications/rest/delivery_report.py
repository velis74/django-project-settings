import json
import logging
import uuid
from gettext import gettext
from typing import Optional

from django.utils.module_loading import import_string
from rest_framework import viewsets
from rest_framework.authentication import BasicAuthentication, TokenAuthentication
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_project_base.licensing.rest.rest import LicenseActionNotImplementedException
from django_project_base.notifications.base.channels.integrations.provider_integration import ProviderIntegration
from django_project_base.notifications.models import DeliveryReport


class DeliveryReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    authentication_classes = [TokenAuthentication, BasicAuthentication]

    _primary_key_names = ["id", "pk", "guid", "uuid"]

    def __find_dlr_id(self, params: dict) -> Optional[str]:
        id = next(filter(lambda i: i.lower() in self._primary_key_names, params.keys()), None)
        if id and params.get(id):
            uid = str(params[id])
            try:
                uuid.UUID(uid)
            except ValueError:
                raise ValidationError(ErrorDetail(string="Invalid identifier", code=gettext("invalid")))
            return uid
        logger = logging.getLogger("django")
        logger.exception(
            f"Id not found for delivery report {self.request.query_params} {self.request.data} {self.request.user}"
        )
        return None

    def __update_dlr(self, params) -> Optional[DeliveryReport]:
        if (id := self.__find_dlr_id(params)) and (dlr := DeliveryReport.objects.filter(pk=id).first()):
            dlr.payload = json.dumps(params)
            dlr.save(update_fields=["payload"])
            return dlr
        return None

    def __parse_delivery_report_payload(self, dlr: DeliveryReport):
        provider: ProviderIntegration = import_string(dlr.provider)()
        provider.parse_delivery_report(dlr)

    def list(self, request) -> Response:
        if dlr := self.__update_dlr(request.query_params):
            self.__parse_delivery_report_payload(dlr)
            return Response()
        return Response()

    def create(self, request) -> Response:
        if dlr := self.__update_dlr(request.data):
            self.__parse_delivery_report_payload(dlr)
            return Response()
        return Response()

    def retrieve(self, request, pk=None):
        raise LicenseActionNotImplementedException()

    def update(self, request, pk=None):
        raise LicenseActionNotImplementedException()

    def partial_update(self, request, pk=None):
        raise LicenseActionNotImplementedException()

    def destroy(self, request, pk=None):
        raise LicenseActionNotImplementedException()