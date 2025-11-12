from uuid import uuid4
from datetime import datetime, timedelta
import pytz
from rest_framework import generics, permissions, status
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from knox.models import AuthToken
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    PasswordResetSerializer,
)
from .models import Profile, PasswordChangeCode, UranusUser
from .tasks import (
    send_email_password_reset,
    send_email_to_user,
    send_email_password_change,
)
from .utils import check_temporary_code

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404

from .models import Derogation
from .serializers import (
    DerogationSerializer,
    DerogationCreateSerializer,
    GroupCreateSerializer,
    UserGroupSerializer,
    AddPermissionSerializer,
)
from .permissions import CanAccordDerogation, IsSuperUser

User = UranusUser

utc = pytz.UTC


def set_user_new_password(user, new_password):
    user.set_password(new_password)
    user.save()
    PasswordChangeCode.objects.filter(user=user).delete()


def reset_user_password(user_email, new_password):
    users = UranusUser.objects.filter(email=user_email)
    if len(users) == 1:
        user = users[0]
        set_user_new_password(user, new_password)
        send_email_password_reset.delay(user_email, new_password)
        return True
    return False


class SignUpAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        msg = "Email envoyé. Consulter votre boîte électronique"
        print("Mot de passe: ", request.data["password"])
        send_email_to_user.delay(request.data["email"], request.data["password"])
        token = AuthToken.objects.create(user)
        return Response(
            {
                "users": UserSerializer(
                    user, context=self.get_serializer_context()
                ).data,
                "token": token[1],
                "message": msg,
            }
        )


class SignInAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response(
            {
                "user": UserSerializer(
                    user, context=self.get_serializer_context()
                ).data,
                "token": AuthToken.objects.create(user)[1],
            }
        )


class MainUser(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


##############################################################
# Initiate Password Change
##############################################################
class InitiatePasswordChangeView(generics.GenericAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request):
        password_token = uuid4()
        msg = "Un mail vous a été envoyé avec un code."
        status = 0
        expiry_time = (datetime.now() + timedelta(minutes=15)).replace(tzinfo=utc)
        try:
            PasswordChangeCode.objects.create(
                token=password_token, validity=expiry_time, user=request.user
            )
        except Exception as error:
            print(error)
            status = -1
            msg = "Erreur lors de la génération du code de validation."
        else:
            send_email_password_change.delay(request.user.email, password_token)

        resultat = "Succès"
        if status != 0:
            resultat = "Echec"
        return Response({"Statut": resultat, "Message": msg})


##############################################################
class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            context={"request": request}, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        if check_temporary_code(
            request.user, serializer.validated_data["temporary_code"]
        ):
            set_user_new_password(
                request.user, serializer.validated_data["new_password"]
            )
            return Response(
                {"Statut": "Succès", "Message": "Mot de passe changé avec succès."}
            )
        else:
            return Response({"Statut": "Echec", "Message": "Code non valide."})


######################################################################################
class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        permissions.IsAdminUser,
    ]

    def post(self, request):
        serializer = PasswordResetSerializer(
            context={"request": request}, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        if reset_user_password(
            serializer.validated_data["user_email"],
            serializer.validated_data["new_password"],
        ):
            return Response(
                {
                    "Statut": "Succès",
                    "Message": "Mot de passe réinitialisé avec succès.",
                }
            )
        else:
            return Response(
                {
                    "Statut": "Echec",
                    "Message": "Echec de la réinitialisation du mot de passe.",
                }
            )


class GetHostnameView(generics.RetrieveAPIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request):
        meta_data = str(request.headers.get("host")) + "/messaging/arolitec/ack"
        return Response({"Hostname": meta_data})


######################################################################################
class ProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


# Vues de gestion des dérogations
class DerogationCreateAPIView(generics.CreateAPIView):
    queryset = Derogation.objects.all()
    serializer_class = DerogationCreateSerializer
    permission_classes = [IsAuthenticated, CanAccordDerogation]

    def perform_create(self, serializer):
        serializer.save(user_habilite=self.request.user)


class CheckDerogationAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return None

    def get(self, request, *args, **kwargs):
        derogation = Derogation.objects.filter(
            user_beneficiaire=request.user,
            date_expiration__gt=datetime.now(),
            is_used=False,
        ).first()

        if derogation:
            return Response(
                {
                    "status": "allowed",
                    "message": "Accès autorisé.",
                    "derogation_id": derogation.id,
                    "motif": derogation.motif,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": "denied",
                    "message": "Accès refusé. Aucune dérogation valide trouvée.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )


class ConsumeDerogationAPIView(generics.UpdateAPIView):
    queryset = Derogation.objects.all()
    serializer_class = DerogationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        derogation = self.get_object()

        if derogation.user_beneficiaire != request.user:
            return Response(
                {"detail": ("Vous n'êtes pas autorisé à consommer cette dérogation.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if derogation.is_used:
            return Response(
                {"detail": "Cette dérogation a déjà été consommée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        derogation.is_used = True
        derogation.save()

        return Response(
            {"status": "success", "message": "Dérogation consommée avec succès."},
            status=status.HTTP_200_OK,
        )


# Vues d'administration (gestion des groupes et permissions)
class GroupCreateAPIView(generics.CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupCreateSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]


class AddUsersToGroupAPIView(generics.CreateAPIView):
    serializer_class = UserGroupSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_name = serializer.validated_data["group_name"]
        user_ids = serializer.validated_data["user_ids"]

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            return Response(
                {"detail": f"Le groupe '{group_name}' n'existe pas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        users = User.objects.filter(id__in=user_ids)
        if users.count() != len(user_ids):
            return Response(
                {"detail": "Certains utilisateurs n'ont pas été trouvés."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for user in users:
            user.groups.add(group)

        return Response(
            {
                "message": f"{len(users)} utilisateur(s) ajouté(s) au groupe '{group_name}'."
            },
            status=status.HTTP_200_OK,
        )


class AddPermissionToUserAPIView(generics.CreateAPIView):
    serializer_class = AddPermissionSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        permission_name = serializer.validated_data["permission_name"]

        user = get_object_or_404(User, pk=user_id)

        try:
            permission = Permission.objects.get(codename=permission_name)
        except Permission.DoesNotExist:
            return Response(
                {"detail": f"La permission '{permission_name}' n'existe pas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.user_permissions.add(permission)

        return Response(
            {
                "message": f"Permission '{permission_name}' accordée à l'utilisateur '{user.username}'."
            },
            status=status.HTTP_200_OK,
        )
