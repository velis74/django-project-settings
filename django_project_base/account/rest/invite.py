import swapper
from django.db import transaction
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from dynamicforms import fields
from dynamicforms.action import Actions, TableAction, TablePosition
from dynamicforms.mixins import DisplayMode
from dynamicforms.serializers import ModelSerializer
from dynamicforms.template_render.layout import Column, Layout, Row
from dynamicforms.template_render.responsive_table_layout import ResponsiveTableLayout, ResponsiveTableLayouts
from dynamicforms.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from django_project_base.account.middleware import ProjectNotSelectedError
from django_project_base.base.exceptions import InviteActionNotImplementedException
from django_project_base.notifications.email_notification import EMailNotificationWithListOfEmails
from django_project_base.notifications.models import DjangoProjectBaseMessage
from django_project_base.utils import get_host_url


class AcceptedField(fields.BooleanField):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.read_only = True

    def to_representation(self, value, row_data=None):
        if row_data and row_data.accepted:
            return True
        return False


class ProjectUserInviteSerializer(ModelSerializer):
    template_context = dict(url_reverse="project-user-invite")
    form_titles = {
        "table": "",
        "new": _("Inviting project member"),
        "edit": "",
    }

    actions = Actions(
        TableAction(TablePosition.HEADER, _("Add"), title=_("Add new record"), name="add", icon="add-circle-outline"),
        add_form_buttons=True,
        add_default_filter=True,
        add_default_crud=False,
    )

    id = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)
    send_by = fields.AutoGeneratedField(display=DisplayMode.HIDDEN)
    project = fields.PrimaryKeyRelatedField(
        display=DisplayMode.SUPPRESS,
        queryset=swapper.load_model("django_project_base", "Project").objects.all(),
    )
    accepted = AcceptedField(display_form=DisplayMode.HIDDEN)
    host_url = fields.CharField(read_only=True, display=DisplayMode.SUPPRESS)

    # def confirm_create_text(self):
    #     owner_change_data = get_owner_change_data(self.context)
    #     if owner_change_data:
    #         return change_owner_warning(owner_change_data.get("free_projects_number"))
    #     return False
    #
    # def confirm_create_title(self):
    #     return _("Create project user invite confirmation")

    # def create(self, validated_data):
    # languages = validated_data.pop("languages")
    # validated_data["send_by"] = self.context["request"].user
    # invite = ProjectUserInvite.objects.create(**validated_data)
    # invite.languages.set(languages)
    #
    # # send email/generate url
    # invite_url = (
    #     ("https" if not settings.DEBUG else "http")
    #     + "://"
    #     + self.context["request"].get_host()
    #     + reverse("signup")
    #     + "%sinvitation_id=%s" % ("/?", str(invite.guid))
    # )
    # user_invite_created.send(sender=ProjectUserInvite, user_invite=invite, user_invite_url=invite_url)

    # return super().create()

    class Meta:
        model = swapper.load_model("django_project_base", "Invite")
        exclude = ()
        responsive_columns = ResponsiveTableLayouts(
            layouts=[
                ResponsiveTableLayout(
                    "email",
                    "accepted",
                    auto_add_non_listed_columns=False,
                ),
            ],
            auto_generate_single_row_layout=False,
        )
        layout = Layout(
            Row(Column("email")),
            Row(
                Column("accepted"),
            ),
            size="large",
        )


class ProjectUserInviteViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectUserInviteSerializer

    def get_queryset(self):
        project = self.request.selected_project
        try:
            return swapper.load_model("django_project_base", "Invite").objects.filter(project_id=project)
        except ProjectNotSelectedError:
            return swapper.load_model("django_project_base", "ProjectMember").objects.none()

    def new_object(self: ModelViewSet):
        new_object = super().new_object()
        if project := self.request.selected_project:
            new_object.project = project
        return new_object

    def retrieve(self: ModelViewSet, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        self.request.data["project"] = self.request.selected_project.pk
        self.request.data["send_by"] = self.request.user.userprofile
        self.request.data["host_url"] = get_host_url(request)
        created = super().create(request, *args, **kwargs)
        EMailNotificationWithListOfEmails(
            message=DjangoProjectBaseMessage(
                subject=_("You are invited to project") + f" {self.request.selected_project.name}",
                body="sdfsdfsdf  asdfadfaf",
                footer="",
                content_type=DjangoProjectBaseMessage.HTML,
            ),
            recipients=[self.request.data["email"]],
            project=self.request.selected_project.slug,
            user=self.request.user.pk,
        ).send()
        return created

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        raise InviteActionNotImplementedException

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        raise InviteActionNotImplementedException

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        raise InviteActionNotImplementedException

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(exclude=True)
    @action(
        methods=["GET"],
        detail=False,
        url_name="accept",
        url_path="accept/(?P<pk>[0-9a-f-]+)'",
    )
    def accept(self, request: Request, pk: str, *args, **kwargs) -> HttpResponse:
        # check if exists

        # ...
        return HttpResponse()
