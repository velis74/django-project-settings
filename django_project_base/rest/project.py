from typing import Union

import swapper
from django.conf import settings
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from dynamicforms import fields
from dynamicforms.mixins import DisplayMode
from dynamicforms.serializers import ModelSerializer
from dynamicforms.template_render.layout import Layout, Row
from dynamicforms.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from django_project_base.utils import get_pk_name


class ProjectSerializer(ModelSerializer):
    template_context = dict(url_reverse="project-base-project")

    def __init__(self, *args, is_filter: bool = False, **kwds):
        super().__init__(*args, is_filter=is_filter, **kwds)

        if self.context.get("view") and self.context["view"].format_kwarg == "componentdef":
            self.fields.fields["owner"].display_table = DisplayMode.SUPPRESS
            if self.context["view"].detail and self.instance.pk is None:
                # we are rendering new form
                self.fields.fields["owner"].display_form = DisplayMode.HIDDEN

    # logo = fields.FileField(display=DisplayMode.SUPPRESS, required=False)  # todo: not implemented UI
    owner = fields.AutoGeneratedField(display_table=DisplayMode.SUPPRESS, display_form=DisplayMode.HIDDEN)

    class Meta:
        model = swapper.load_model("django_project_base", "Project")
        exclude = ("logo",)  # TODO we currently don't support logos well. see DPB #3
        layout = Layout(Row("name"), Row("slug"), Row("description"))


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer

    def new_object(self: ModelViewSet):
        new_object = super().new_object()
        if self.request and self.request.user and self.request.user.is_authenticated:
            new_object.owner = getattr(
                self.request.user, swapper.load_model("django_project_base", "Profile")._meta.model_name
            )

        return new_object

    @staticmethod
    def _get_queryset_for_request(request):
        qs = swapper.load_model("django_project_base", "Project").objects
        # todo: request.user.is_authenticated this should be solved with permission class
        if not request or not request.user or not request.user.is_authenticated:
            return qs.none()
        user_profile = getattr(request.user, swapper.load_model("django_project_base", "Profile")._meta.model_name)
        # projects where current user is owner
        owned_projects = qs.filter(owner=user_profile)
        # projects where user is member
        member_projects = qs.filter(members__member=user_profile)

        return (owned_projects | member_projects).distinct()

    def get_queryset(self):
        return ProjectViewSet._get_queryset_for_request(self.request)

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)

    @extend_schema(
        description="Get currently selected project",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="current",
        url_name="project-current",
        permission_classes=[IsAuthenticated],
    )
    def get_current_project(self, request: Request, **kwargs) -> Response:
        current_project_attr = (
            getattr(settings, "DJANGO_PROJECT_BASE_BASE_REQUEST_URL_VARIABLES", {})
            .get("project", {})
            .get("value_name", None)
        )
        if current_project_attr is None:
            raise NotFound("Current project resolution not set up for project")
        if (current_project_slug := getattr(request, current_project_attr, None)) is None:
            raise NotFound("Current project not specified for request")

        current_project = swapper.load_model("django_project_base", "Project").objects.get(slug=current_project_slug)
        serializer = self.get_serializer(current_project)
        return Response(serializer.data)

    @extend_schema(
        description="Marks profile of calling user for deletion in future. Future date is determined " "by settings",
        responses={
            status.HTTP_200_OK: OpenApiResponse(description="OK"),
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="No content"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Not allowed"),
        },
    )
    @get_current_project.mapping.post
    def update_current_profile(self, request: Request, **kwargs) -> Response:
        current_project_attr = (
            getattr(settings, "DJANGO_PROJECT_BASE_BASE_REQUEST_URL_VARIABLES", {})
            .get("project", {})
            .get("value_name", None)
        )
        if current_project_attr is None:
            raise NotFound("Current project resolution not set up for project")
        if (current_project_slug := getattr(request, current_project_attr, None)) is None:
            raise NotFound("Current project not specified for request")

        current_project = swapper.load_model("django_project_base", "Project").objects.get(slug=current_project_slug)

        serializer = self.get_serializer(current_project, data=request.data, many=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        SLUG_FIELD_NAME: str = settings.DJANGO_PROJECT_BASE_SLUG_FIELD_NAME

        lookup_field: str = self.lookup_field
        lookup_field_val: Union[str, int] = self.kwargs.get(self.lookup_field)

        proj_value_name = settings.DJANGO_PROJECT_BASE_BASE_REQUEST_URL_VARIABLES["project"]["value_name"]
        if getattr(self.request, proj_value_name, None) and lookup_field_val != "new":
            lookup_field_val = getattr(self.request, proj_value_name)

        def set_args(name: str) -> None:
            self.kwargs.pop(lookup_field, None)
            self.kwargs[name] = lookup_field_val
            self.lookup_field = name

        if lookup_field == "pk" or lookup_field == get_pk_name(self.get_queryset()):
            is_pk_auto_field: bool = self.get_queryset().model._meta.pk.get_internal_type() == "AutoField"
            try:
                int(lookup_field_val) if is_pk_auto_field and lookup_field_val else None
                return super().get_object()
            except (ValueError, Http404):
                set_args(SLUG_FIELD_NAME)
                return super().get_object()
        return super().get_object()

    def create(self, request, *args, **kwargs):
        create_response = super().create(request, *args, **kwargs)
        project = swapper.load_model("django_project_base", "Project").objects.get(slug=create_response.data["slug"])
        swapper.load_model("django_project_base", "ProjectMember").objects.create(project=project, member=request.user)
        return create_response
