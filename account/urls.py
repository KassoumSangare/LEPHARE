from django.urls import path, include
from .views import (
    SignUpAPI,
    SignInAPI,
    MainUser,
    ChangePasswordView,
    ProfileViewSet,
    InitiatePasswordChangeView,
    ResetPasswordView,
    GetHostnameView,
    DerogationCreateAPIView,
    CheckDerogationAPIView,
    ConsumeDerogationAPIView,
    GroupCreateAPIView,
    AddUsersToGroupAPIView,
    AddPermissionToUserAPIView,
)
from knox import views as knox_views
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r"users/profile", ProfileViewSet)

urlpatterns = [
    # Endpoints de gestion des dérogations
    path(
        "derogations/create/",
        DerogationCreateAPIView.as_view(),
        name="api_create_derogation",
    ),
    path(
        "derogations/check/",
        CheckDerogationAPIView.as_view(),
        name="api_check_derogation",
    ),
    path(
        "derogations/<int:pk>/consume/",
        ConsumeDerogationAPIView.as_view(),
        name="api_consume_derogation",
    ),
    # Endpoints de gestion administrative
    path("admin/groups/create/", GroupCreateAPIView.as_view(), name="api_create_group"),
    path(
        "admin/groups/add-users/",
        AddUsersToGroupAPIView.as_view(),
        name="api_add_users_to_group",
    ),
    path(
        "admin/users/add-permission/",
        AddPermissionToUserAPIView.as_view(),
        name="api_add_permission_to_user",
    ),
]

urlpatterns = [
    path(r"users/", include("knox.urls")),
    path(r"users/register", SignUpAPI.as_view(), name="account_register"),
    path(r"users/login", SignInAPI.as_view(), name="account_login"),
    path(r"users/user", MainUser.as_view(), name="account_user"),
    path(
        r"users/initiatepasswordchange",
        InitiatePasswordChangeView.as_view(),
        name="account_initiate_passwordchange",
    ),
    path(
        r"users/changepassword",
        ChangePasswordView.as_view(),
        name="account_changepassword",
    ),
    path(r"users/logout", knox_views.LogoutView.as_view(), name="account_logout"),
    path(
        r"users/logoutall", knox_views.LogoutAllView.as_view(), name="account_logoutall"
    ),
    path(
        r"users/resetpassword",
        ResetPasswordView.as_view(),
        name="account_resetpassword",
    ),
    path(
        r"users/gethostname",
        GetHostnameView.as_view(),
        name="get_hostname",
    ),
    # Endpoints de gestion des dérogations
    path(
        r"derogations/create",
        DerogationCreateAPIView.as_view(),
        name="api_create_derogation",
    ),
    path(
        r"derogations/check",
        CheckDerogationAPIView.as_view(),
        name="api_check_derogation",
    ),
    path(
        r"derogations/<int:pk>/consume",
        ConsumeDerogationAPIView.as_view(),
        name="api_consume_derogation",
    ),
    # Endpoints de gestion administrative
    path(r"admin/groups/create", GroupCreateAPIView.as_view(), name="api_create_group"),
    path(
        r"admin/groups/add_users",
        AddUsersToGroupAPIView.as_view(),
        name="api_add_users_to_group",
    ),
    path(
        r"admin/users/add_permission",
        AddPermissionToUserAPIView.as_view(),
        name="api_add_permission_to_user",
    ),
    path("", include(router.urls)),
]
