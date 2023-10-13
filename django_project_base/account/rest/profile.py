import datetime
import uuid
from random import randrange

import django
import swapper
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.db import transaction
from django.db.models import ForeignKey, Model, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from dynamicforms import fields
from dynamicforms.action import TableAction, TablePosition
from dynamicforms.mixins import DisplayMode
from dynamicforms.serializers import ModelSerializer
from dynamicforms.template_render.layout import Column, Layout, Row
from dynamicforms.template_render.responsive_table_layout import ResponsiveTableLayout, ResponsiveTableLayouts
from dynamicforms.viewsets import ModelViewSet
from natural.date import compress
from rest_framework import exceptions, filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.fields import IntegerField
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_registration.exceptions import UserNotFound

from django_project_base.account.constants import MERGE_USERS_QS_CK
from django_project_base.account.middleware import ProjectNotSelectedError
from django_project_base.account.rest.project_profiles_utils import get_project_members
from django_project_base.base.event import UserRegisteredEvent
from django_project_base.constants import NOTIFY_NEW_USER_SETTING_NAME
from django_project_base.notifications.email_notification import (
    EMailNotificationWithListOfEmails,
    SystemEMailNotification,
)
from django_project_base.notifications.models import DjangoProjectBaseMessage
from django_project_base.permissions import BasePermissions
from django_project_base.rest.project import ProjectSerializer, ProjectViewSet
from django_project_base.settings import DELETE_PROFILE_TIMEDELTA, USER_CACHE_KEY
from django_project_base.utils import get_pk_name

search_fields = ["username", "email", "first_name", "last_name"]


class ProfilePermissionsField(fields.ManyRelatedField):
    @staticmethod
    def to_dict(permission: Permission) -> dict:
        return {
            get_pk_name(Permission): permission.pk,
            "codename": permission.codename,
            "name": permission.name,
        }

    def to_representation(self, value, row_data=None):
        if row_data and row_data.pk:
            return [ProfilePermissionsField.to_dict(p) for p in row_data.user_permissions.all()]
        return []


class ProfileGroupsField(fields.ManyRelatedField):
    def to_representation(self, value, row_data=None):
        if row_data and row_data.pk:
            return [
                {
                    get_pk_name(Group): g.pk,
                    "permissions": [ProfilePermissionsField.to_dict(p) for p in g.permissions.all()],
                    "name": g.name,
                }
                for g in row_data.groups.all()
            ]
        return []


class ProfileSerializer(ModelSerializer):
    template_context = dict(url_reverse="profile-base-project")

    form_titles = {
        "table": "User profiles",
        "new": "New user",
        "edit": "Edit user",
    }

    id = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)
    username = fields.AutoGeneratedField(display_table=DisplayMode.HIDDEN)
    first_name = fields.AutoGeneratedField(display_table=DisplayMode.HIDDEN)
    last_name = fields.AutoGeneratedField(display_table=DisplayMode.HIDDEN)
    bio = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    theme = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    password = fields.AutoGeneratedField(
        password_field=True, display=DisplayMode.HIDDEN, write_only=True, required=False
    )
    last_login = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    date_joined = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    is_active = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    is_superuser = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    is_staff = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)  # read_only=True,
    avatar = fields.AutoGeneratedField(display_table=DisplayMode.HIDDEN)
    reverse_full_name_order = fields.AutoGeneratedField(display_table=DisplayMode.HIDDEN)

    full_name = fields.CharField(read_only=True, display_form=DisplayMode.HIDDEN)
    is_impersonated = fields.SerializerMethodField(display=DisplayMode.HIDDEN)
    password_invalid = fields.BooleanField(display_form=DisplayMode.HIDDEN, display_table=DisplayMode.HIDDEN)

    delete_at = fields.DateTimeField(read_only=True, display=DisplayMode.HIDDEN)
    permissions = ProfilePermissionsField(
        source="user_permissions",
        child_relation=fields.PrimaryKeyRelatedField(
            help_text=_("Specific permissions for this user"), queryset=Permission.objects.all(), required=False
        ),
        help_text=_("Specific permissions for this user"),
        required=False,
        allow_null=False,
        read_only=True,
        display=DisplayMode.SUPPRESS,
    )

    groups = ProfileGroupsField(
        child_relation=fields.PrimaryKeyRelatedField(
            help_text=_(
                "The groups this user belongs to. A user will get all permissions granted to each of their groups."
            ),
            queryset=Group.objects.all(),
            required=False,
        ),
        help_text=_(
            "The groups this user belongs to. A user will get all permissions granted to each of their groups."
        ),
        required=False,
        allow_null=False,
        read_only=True,
        display=DisplayMode.SUPPRESS,
    )

    def __init__(self, *args, is_filter: bool = False, **kwds):
        super().__init__(*args, is_filter=is_filter, **kwds)
        request = self._context["request"]

        if not request.user.is_superuser:
            self.fields.pop("is_staff", None)
            self.fields.pop("is_superuser", None)

        if (
            self.instance
            and not isinstance(self.instance, (list, QuerySet, dict))
            and self.instance.pk != request.user.pk
        ):
            # only show this field to the user for their account. admins don't see this field
            self.fields.pop("reverse_full_name_order", None)

        is_record_view = len(args) == 1 and isinstance(args[0], swapper.load_model("django_project_base", "Profile"))
        if not is_record_view:
            # for table view, we remove permissions and groups to improve performance
            self.fields.pop("permissions", None)
            self.fields.pop("groups", None)

        if str(request.query_params.get("remove-merge-users", "false")) in tuple(
            map(str, fields.BooleanField.TRUE_VALUES)
        ) and (request.user.is_superuser or request.user.is_staff):
            self.actions.actions.append(
                TableAction(
                    TablePosition.ROW_END,
                    label=_("Merge"),
                    title=_("Merge"),
                    name="add-to-merge",
                    icon="git-merge-outline",
                ),
            )

        if request.user.is_superuser or request.user.is_staff:
            self.actions.actions.append(
                TableAction(
                    TablePosition.HEADER,
                    label=_("Export"),
                    title=_("Export"),
                    name="export",
                    icon="download-outline",
                )
            )

    def get_is_impersonated(self, obj):
        try:
            request = self.context["request"]
            session = request.session
            return bool(session.get("hijack_history", [])) and obj.id == request.user.id
        except:
            pass
        return False

    class Meta:
        model = swapper.load_model("django_project_base", "Profile")
        exclude = ("user_permissions",)
        layout = Layout(
            Row(Column("username"), Column("password")),
            Row(Column("first_name"), Column("last_name")),
            # Row("reverse_full_name_order"),
            Row("email"),
            Row("phone_number"),
            Row("language"),
            Row("avatar"),
            columns=2,
            size="large",
        )
        responsive_columns = ResponsiveTableLayouts(
            auto_generate_single_row_layout=True,
            layouts=[
                ResponsiveTableLayout(auto_add_non_listed_columns=True),
                ResponsiveTableLayout("full_name", "email", "#actions-row_end", auto_add_non_listed_columns=False),
            ],
        )


class ProfileRegisterSerializer(ProfileSerializer):
    password = fields.CharField(label=_("Password"), password_field=True)
    password_repeat = fields.CharField(label=_("Repeat Password"), password_field=True)

    class Meta(ProfileSerializer.Meta):
        layout = Layout(
            Row(Column("username")),
            Row(Column("first_name"), Column("last_name")),
            Row("password"),
            Row("password_repeat"),
            Row("email"),
            Row("phone_number"),
            Row("language"),
            columns=2,
            size="large",
        )
        exclude = ProfileSerializer.Meta.exclude + ("avatar",)

    def validate(self, attrs):
        super().validate(attrs)
        errors = {}
        password_repeat = attrs.pop("password_repeat")
        if not attrs["password"]:
            errors["password"] = _("Password is required")
        if not attrs["password"] == password_repeat:
            errors["password_repeat"] = _("Passwords do not match")

        if not attrs["email"]:
            errors["email"] = _("Email is required")

        if errors:
            raise ValidationError(errors)
        return attrs


class MergeUserRequest(Serializer):
    user = IntegerField(min_value=1, required=True, allow_null=False)


class ProfileViewPermissions(BasePermissions):
    """
    Allows users to have full permissions on get/post (retrieving and adding new users).
    Other methods require authentication.
    """

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        if request.method == "GET" and request.path.split("/")[-1].split(".")[0] == "new":
            return True
        return super().has_permission(request, view)


@extend_schema_view(
    create=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
)
class ProfileViewSet(ModelViewSet):
    filter_backends = [filters.SearchFilter]
    search_fields = search_fields
    permission_classes = (ProfileViewPermissions,)
    pagination_class = ModelViewSet.generate_paged_loader(30, ["un_sort", "id"])

    def get_queryset(self):
        return get_project_members(self.request)

    def get_serializer_class(self):
        if self.request.query_params.get("select", "") == "1":

            class SearchProfileSerializer(ProfileSerializer):
                class Meta(ProfileSerializer.Meta):
                    fields = search_fields + [get_pk_name(get_user_model()), "full_name"]
                    exclude = None

            return SearchProfileSerializer

        return ProfileSerializer

    def filter_queryset_field(self, queryset, field, value):
        if field == "full_name":
            return queryset.filter(un__icontains=value)
        return super().filter_queryset_field(queryset, field, value)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "search", description="Search users by all of those fields: username, email, first_name, last_name"
            )
        ],
        description="Get list of users",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK", response=get_serializer_class),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Default parameters for user registration",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="register",
        url_name="profile-register",
        permission_classes=[],
    )
    def register_account(self, request: Request, **kwargs):
        register_flow_identifier = str(uuid.uuid4())
        response = Response(ProfileRegisterSerializer(None, context=self.get_serializer_context()).data)
        response.set_cookie(
            "register-flow",
            register_flow_identifier,
            max_age=settings.CONFIRMATION_CODE_TIMEOUT,
            httponly=True,
            samesite="Strict",
        )
        cache.set(register_flow_identifier, get_random_string(length=6), timeout=settings.CONFIRMATION_CODE_TIMEOUT)
        return response

    @extend_schema(
        description="Registering new account",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @register_account.mapping.post
    @transaction.atomic
    def create_new_account(self, request: Request, **kwargs):
        # set default values
        request.data["date_joined"] = datetime.datetime.now()
        request.data["is_active"] = False

        # call serializer to do the data processing drf way - hijack
        serializer = ProfileRegisterSerializer(
            None, context=self.get_serializer_context(), data=request.data, many=False
        )
        serializer.is_valid(raise_exception=True)

        if get_user_model().objects.filter(email=serializer.validated_data["email"]).exists():
            # TODO: https://taiga.velis.si/project/velis-django-project-admin/issue/711
            raise ValidationError()

        user = serializer.save()
        user.set_password(request.data["password"])
        user.save()
        UserRegisteredEvent(user=user).trigger(payload=request)
        return Response(serializer.validated_data)

    @extend_schema(
        description="Get user profile by id",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK", response=get_serializer_class),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Update profile data (partially)",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK", response=get_serializer_class),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        description="Get user profile of calling user.",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="current",
        url_name="profile-current",
        permission_classes=[IsAuthenticated],
    )
    def get_current_profile(self, request: Request, **kwargs) -> Response:
        user: Model = request.user
        serializer = self.get_serializer(user)
        response_data: dict = serializer.data
        if getattr(request, "GET", None) and request.GET.get("decorate", "") == "default-project":
            try:
                response_data["default_project"] = ProjectSerializer(request.selected_project).data
            except ProjectNotSelectedError:
                if project_object := ProjectViewSet._get_queryset_for_request(request).first():
                    response_data["default_project"] = ProjectSerializer(project_object).data
                else:
                    response_data["default_project"] = None
        return Response(response_data)

    @extend_schema(
        description="Marks profile of calling user for deletion in future. Future date is determined " "by settings",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @get_current_profile.mapping.post
    def update_current_profile(self, request: Request, **kwargs) -> Response:
        user: Model = request.user
        new_email = request.data.pop("email", None)
        serializer = self.get_serializer(user, data=request.data, many=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email_changed = new_email and user.email != new_email
        response = Response(serializer.data)
        if email_changed:
            code = randrange(100001, 999999)
            response.set_cookie("verify-email", user.pk, samesite="Lax")
            request.session[f"email-changed-{code}-{user.pk}"] = new_email
            # TODO: Use system email
            # TODO: SEND THIS AS SYSTEM MSG WHEN PR IS MERGED
            # TODO: https://taiga.velis.si/project/velis-django-project-admin/issue/728
            EMailNotificationWithListOfEmails(
                message=DjangoProjectBaseMessage(
                    subject=f"{_('Email change for account on')} {request.META['HTTP_HOST']}",
                    body=f"{_('You requested an email change for your account at')} {request.META['HTTP_HOST']}. "
                    f"\n\n{_('Your verification code is')}: "
                    f"{code} \n\n {_('Code is valid for')} {compress(settings.CONFIRMATION_CODE_TIMEOUT)}.\n",
                    footer="",
                    content_type=DjangoProjectBaseMessage.PLAIN_TEXT,
                ),
                recipients=[new_email],
                project=self.request.selected_project.slug,
                user=user.pk,
            ).send()
        return response

    @extend_schema(exclude=True)
    @action(
        methods=["POST"],
        detail=False,
        url_path="confirm-new-email",
        url_name="confirm-new-email",
    )
    @transaction.atomic()
    def confirm_new_email(self, request: Request, **kwargs) -> Response:
        user = request.user
        if not request.data.get("code"):
            raise ValidationError(dict(code=[_("Code required")]))
        key = f"email-changed-{request.data['code']}-{user.pk}"
        new_email = request.session.get(key)
        if email := new_email:
            user.email = email
            user.save(update_fields=["email"])
            request.session.pop(key, None)
            response = Response()
            response.delete_cookie("verify-email")
            return response
        raise ValidationError(dict(code=[_("Invalid code")]))

    @extend_schema(
        description="Marks profile of calling user for deletion in future. Future date is determined " "by settings",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @get_current_profile.mapping.delete
    def mark_current_profile_delete(self, request: Request, **kwargs) -> Response:
        user: Model = getattr(request, "user", None)
        if not user:
            raise exceptions.AuthenticationFailed
        # user.is_active = False // user must still be able to login
        profile_obj = getattr(user, swapper.load_model("django_project_base", "Profile")._meta.model_name)
        profile_obj.delete_at = timezone.now() + datetime.timedelta(days=DELETE_PROFILE_TIMEDELTA)

        profile_obj.save(update_fields=["delete_at"])
        # user.save(update_fields=["is_active"])
        cache.delete(USER_CACHE_KEY.format(id=user.id))
        request.session.flush()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Immediately removes user from database",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        raise exceptions.PermissionDenied

    @extend_schema(exclude=True)
    @action(
        methods=["POST"],
        detail=False,
        url_path="merge-accounts",
        url_name="merge-accounts",
        permission_classes=[IsAuthenticated],
    )
    def merge_accounts(self, request, *args, **kwargs):
        from rest_registration.settings import registration_settings

        serializer = registration_settings.LOGIN_SERIALIZER_CLASS(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_user = self.request.user
        auth_user_is_main = str(self.request.data.get("account", "false")) in fields.BooleanField.TRUE_VALUES
        try:
            from django_project_base.account.service.merge_users_service import MergeUsersService

            user = registration_settings.LOGIN_AUTHENTICATOR(serializer.validated_data, serializer=serializer)
            MergeUserGroup = swapper.load_model("django_project_base", "MergeUserGroup")

            group, created = MergeUserGroup.objects.get_or_create(
                users=f"{auth_user.pk},{user.pk}", created_by=self.request.user.pk
            )
            MergeUsersService().handle(user=auth_user if auth_user_is_main else user, group=group)
            if not auth_user_is_main:
                # logout current user and redirect to login
                request.session.flush()
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        except UserNotFound:
            raise UserNotFound
        except Exception:
            raise APIException

    @extend_schema(exclude=True)
    @action(
        methods=["POST"],
        detail=False,
        url_path="merge",
        url_name="merge",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def merge(self, request: Request, **kwargs) -> Response:
        ser = MergeUserRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        ck = MERGE_USERS_QS_CK % self.request.user.pk
        ck_val = cache.get(ck, [])
        ck_val.append(ser.validated_data["user"])
        cache.set(ck, list(set(ck_val)), timeout=None)
        return Response(status=status.HTTP_201_CREATED)

    @extend_schema(exclude=True)
    @action(
        methods=["POST"],
        detail=False,
        url_path="reset-user-data",
        url_name="reset-user-data",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic()
    def reset_user_data(self, request: Request, **kwargs) -> Response:
        profile_model = swapper.load_model("django_project_base", "Profile")
        profile_obj = getattr(request.user, profile_model._meta.model_name)
        if request.data.get("reset"):
            base_user_models = (get_user_model(), profile_model)
            for mdl in django.apps.apps.get_models(include_auto_created=True, include_swapped=True):
                if mdl not in base_user_models and not mdl._meta.abstract and not mdl._meta.swapped:
                    for fld in [
                        f
                        for f in mdl._meta.fields
                        if isinstance(f, ForeignKey) and (f.related_model in base_user_models)
                    ]:
                        mdl.objects.filter(**{fld.attname: fld.to_python(profile_obj.pk)}).delete()
        profile_obj.delete_at = None
        profile_obj.save(update_fields=["delete_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        project = swapper.load_model("django_project_base", "Project").objects.get(
            slug=getattr(self.request, settings.DJANGO_PROJECT_BASE_BASE_REQUEST_URL_VARIABLES["project"]["value_name"])
        )
        if (
            sett := swapper.load_model("django_project_base", "ProjectSettings")
            .objects.filter(name=NOTIFY_NEW_USER_SETTING_NAME, project=project)
            .first()
        ) and sett.python_value:
            recipients = [response.data[get_pk_name(get_user_model())]]
            SystemEMailNotification(
                message=DjangoProjectBaseMessage(
                    subject=_("Your account was created for you"),
                    body=render_to_string(
                        "account_created.html",
                        {
                            "username": f"{response.data['username']}/{response.data['email']}",
                        },
                    ),
                    footer="",
                    content_type=DjangoProjectBaseMessage.HTML,
                ),
                project=project.slug,
                recipients=recipients,
                user=self.request.user.pk,
            ).send()

        return response


class ProjectsProfileSearchViewSet(ProfileViewSet):
    def get_queryset(self):
        projects = set(map(lambda pm: pm.project, self.request.user.projects.all()))
        first_project = next(iter(projects), None)
        if not first_project:
            return swapper.load_model("django_project_base", "Profile").objects.none()
        qs = get_project_members(self.request, project=first_project)
        projects = projects - {first_project}
        for project in projects:
            qs = qs | get_project_members(self.request, project=project)
        return qs.distinct()
