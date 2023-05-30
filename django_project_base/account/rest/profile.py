import datetime

import swapper
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.db.models import Case, CharField, Model, Value, When
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from dynamicforms import fields
from dynamicforms.mixins import DisplayMode
from dynamicforms.serializers import ModelSerializer
from dynamicforms.template_render.layout import Column, Layout, Row
from dynamicforms.template_render.responsive_table_layout import ResponsiveTableLayout, ResponsiveTableLayouts
from dynamicforms.viewsets import ModelViewSet
from rest_framework import exceptions, filters, status
from rest_framework.decorators import action, permission_classes as permission_classes_decorator
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from django_project_base.rest.project import ProjectSerializer
from django_project_base.settings import DELETE_PROFILE_TIMEDELTA, USER_CACHE_KEY


class ProfilePermissionsField(fields.ManyRelatedField):
    @staticmethod
    def to_dict(permission: Permission) -> dict:
        return {
            Permission._meta.pk.name: permission.pk,
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
                    Group._meta.pk.name: g.pk,
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

    full_name = fields.CharField(read_only=True)
    is_impersonated = fields.SerializerMethodField()

    delete_at = fields.DateTimeField(write_only=True)
    permissions = ProfilePermissionsField(
        source="user_permissions",
        child_relation=fields.PrimaryKeyRelatedField(
            help_text=_("Specific permissions for this user"), queryset=Permission.objects.all(), required=False
        ),
        help_text=_("Specific permissions for this user"),
        required=False,
        allow_null=False,
        read_only=True,
        display=DisplayMode.HIDDEN,
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
        display=DisplayMode.HIDDEN,
    )

    def __init__(self, *args, is_filter: bool = False, **kwds):
        super().__init__(*args, is_filter=is_filter, **kwds)
        if not self._context.get("request").user.is_superuser:
            self.fields.pop("is_staff", None)
            self.fields.pop("is_superuser", None)

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
        changed_flds = {
            "id": dict(display=DisplayMode.HIDDEN),
            "full_name": dict(read_only=True, display_form=DisplayMode.HIDDEN),
            "username": dict(display_table=DisplayMode.HIDDEN),
            "first_name": dict(display_table=DisplayMode.HIDDEN),
            "last_name": dict(display_table=DisplayMode.HIDDEN),
            "is_impersonated": dict(read_only=True, display=DisplayMode.HIDDEN),
            "bio": dict(read_only=True, display=DisplayMode.HIDDEN),
            "theme": dict(read_only=True, display=DisplayMode.HIDDEN),
            "password": dict(password_field=True, display=DisplayMode.HIDDEN),
            "delete_at": dict(read_only=True, display=DisplayMode.HIDDEN),
            "last_login": dict(read_only=True, display=DisplayMode.HIDDEN),
            "date_joined": dict(read_only=True, display=DisplayMode.HIDDEN),
            "is_active": dict(read_only=True, display=DisplayMode.HIDDEN),
            "is_superuser": dict(read_only=True, display=DisplayMode.HIDDEN),
            "is_staff": dict(read_only=True, display=DisplayMode.HIDDEN),
            "avatar": dict(display_table=DisplayMode.HIDDEN),
            "reverse_full_name_order": dict(display_table=DisplayMode.HIDDEN),
        }
        layout = Layout(
            Row(Column("username"), Column("password")),
            Row(Column("first_name"), Column("last_name")),
            Row("reverse_full_name_order"),
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
                ResponsiveTableLayout("full_name", "email", auto_add_non_listed_columns=False),
                ResponsiveTableLayout(["full_name", "email"], auto_add_non_listed_columns=False),
            ],
        )


@extend_schema_view(
    create=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
)
class ProfileViewSet(ModelViewSet):
    serializer_class = ProfileSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "email", "first_name", "last_name"]
    permission_classes = [IsAuthenticated]
    pagination_class = ModelViewSet.generate_paged_loader(30, ["un_sort", "id"])

    def get_queryset(self):
        qs = swapper.load_model("django_project_base", "Profile").objects.annotate(
            un=Concat(
                Coalesce(
                    Case(When(first_name="", then="username"), default="first_name", output_field=CharField()),
                    Value(""),
                ),
                Value(" "),
                Coalesce(
                    Case(When(last_name="", then="username"), default="last_name", output_field=CharField()),
                    "username",
                ),
            ),
            un_sort=Concat(
                Coalesce(
                    Case(When(last_name="", then="username"), default="last_name", output_field=CharField()),
                    "username",
                ),
                Value(" "),
                Coalesce(
                    Case(When(first_name="", then="username"), default="first_name", output_field=CharField()),
                    Value(""),
                ),
            ),
        )

        if getattr(self.request, "current_project_slug", None):
            # if current project was parsed from request, filter profiles to current project only
            qs = qs.filter(projects__project__slug=self.request.current_project_slug)
        elif not (self.request.user.is_staff or self.request.user.is_superuser):
            # but if user is not an admin, and the project is not known, only return this user's project
            qs = qs.filter(pk=self.request.user.pk)

        qs = qs.order_by("un", "id")

        return qs.all()

    def get_serializer_class(self):
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
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    def create(self, request: Request, *args, **kwargs) -> Response:
        raise APIException(code=status.HTTP_501_NOT_IMPLEMENTED)
        # return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Get user profile by id",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK", response=get_serializer_class),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Update profile data (partially)",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK", response=get_serializer_class),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).partial_update(request, *args, **kwargs)

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
        serializer = self.get_serializer(
            getattr(user, swapper.load_model("django_project_base", "Profile")._meta.model_name)
        )
        response_data: dict = serializer.data
        if getattr(request, "GET", None) and request.GET.get("decorate", "") == "default-project":
            project_model: Model = swapper.load_model("django_project_base", "Project")
            response_data["default-project"] = None
            if project_model:
                ProjectSerializer.Meta.model = project_model
                response_data["default-project"] = ProjectSerializer(
                    project_model.objects.filter(owner=user).first()
                ).data
        return Response(response_data)

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
        user.is_active = False
        profile_obj = getattr(user, swapper.load_model("django_project_base", "Profile")._meta.model_name)
        profile_obj.delete_at = timezone.now() + datetime.timedelta(days=DELETE_PROFILE_TIMEDELTA)

        profile_obj.save()
        user.save()
        cache.delete(USER_CACHE_KEY.format(id=user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Immediately removes user from database",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
        },
    )
    @permission_classes_decorator([IsAdminUser])
    def destroy(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).destroy(request, *args, **kwargs)
