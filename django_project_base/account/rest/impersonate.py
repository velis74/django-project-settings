import swapper
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiTypes
from dynamicforms import fields, serializers, viewsets
from dynamicforms.action import Actions, FormButtonAction, FormButtonTypes
from hijack.helpers import login_user, release_hijack
from rest_framework import status
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response


class ImpersonateRequestSerializer(serializers.Serializer):
    """
    Impersonation options. Fill out any of the fields to identify the impersonated user
    """

    id = fields.IntegerField(required=False, label=_("User ID"))
    email = fields.EmailField(required=False, label=_("User email"))
    username = fields.CharField(required=False)


class ImpersonateUserDialogSerializer(serializers.Serializer):
    template_context = dict(
        url_reverse="profile-base-impersonate-user", url_reverse_kwargs=None, dialog_header_classes="bg-info"
    )
    form_titles = {"new": "Impersonate a user"}

    id = fields.PrimaryKeyRelatedField(
        queryset=swapper.load_model("django_project_base", "Profile").objects.all(),
        label=_("User"),
        url_reverse="profile-base-project-list",
        query_field="search",
        placeholder=_("Select a user to impersonate"),
        required=False,
        allow_null=True,
    )

    actions = Actions(
        FormButtonAction(btn_type=FormButtonTypes.CANCEL, name="cancel"),
        FormButtonAction(btn_type=FormButtonTypes.SUBMIT, name="submit", label=_("Impersonate")),
        add_form_buttons=False,
    )


@extend_schema_view(
    # create=extend_schema(exclude=True),
    retrieve=extend_schema(
        description="Retrieves dialog definition for impersonation dialog",
        parameters=[OpenApiParameter("id", OpenApiTypes.STR, OpenApiParameter.PATH, enum=["new"])],
    ),
)
class ImpersonateUserViewset(viewsets.SingleRecordViewSet):
    serializer_class = ImpersonateUserDialogSerializer

    def new_object(self):
        return dict(id=None)

    # noinspection PyMethodMayBeStatic
    def __validate(self, req_data: dict) -> dict:
        ser: ImpersonateRequestSerializer = ImpersonateRequestSerializer(data=req_data)
        ser.is_valid(raise_exception=True)
        return ser.validated_data

    @extend_schema(
        request=ImpersonateRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Forbidden. You do not have permission to perform this action or "
                "Impersonating self is not allowed"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="User matching provided data not found"),
        },
        description="Login as another user and work on behalf of other user without having to know their credentials",
    )
    @permission_classes([IsAdminUser])
    def create(self, request: Request, *args, **kwargs) -> Response:
        # def start(self, request: Request) -> Response:
        validated_data: dict = self.__validate(request.data)
        hijacked_user: Model = get_object_or_404(get_user_model(), **validated_data)
        if request.user == hijacked_user:
            raise PermissionDenied(_("Impersonating self is not allowed"))
        login_user(request, hijacked_user)
        return Response()

    @extend_schema(
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Forbidden"),
        },
        description="Logout as another user",
    )
    @permission_classes([IsAuthenticated])
    def destroy(self, request: Request) -> Response:
        release_hijack(request)
        return Response()
