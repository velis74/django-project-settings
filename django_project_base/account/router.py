from dynamicforms.routers import DFRouter

from django_project_base.account.rest.account import (
    ChangePasswordViewSet,
    LoginViewSet,
    LogoutViewSet,
    RegisterViewSet,
    ResetPasswordViewSet,
    SendResetPasswordLinkViewSet,
    VerifyRegistrationViewSet,
)
from django_project_base.account.rest.impersonate import ImpersonateUserViewset
from django_project_base.account.rest.profile import ProfileViewSet

accounts_router = DFRouter(trailing_slash=True)

accounts_router.register(r"", LoginViewSet, basename="account")
accounts_router.register(r"", LogoutViewSet, basename="account")
accounts_router.register(r"change-password", ChangePasswordViewSet, basename="change-password")
accounts_router.register(r"", ResetPasswordViewSet, basename="account")
accounts_router.register(r"", RegisterViewSet, basename="account")
accounts_router.register(r"", SendResetPasswordLinkViewSet, basename="account")
accounts_router.register(r"", VerifyRegistrationViewSet, basename="account")

profile_router = DFRouter(trailing_slash=False)
profile_router.register(r"profile", ProfileViewSet, basename="profile-base-project")
profile_router.register_single_record(r"impersonate", ImpersonateUserViewset, basename="profile-base-impersonate-user")
