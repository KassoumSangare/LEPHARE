from django.contrib.auth import authenticate
from .models import UranusUser, Profile
from .utils import check_temporary_code
from rest_framework import serializers
from django.contrib.auth.models import Group
from .models import Derogation

User = UranusUser


class ProfilResumeSerializer(serializers.ModelSerializer):
    """Profil joint à l'utilisateur (connexion, utilisateur courant) : jamais le code d'accès ASACI."""

    code_acces_configure = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("id", "code_demandeur", "code_acces_configure")

    def get_code_acces_configure(self, obj):
        return bool(obj.code_acces)


class UserSerializer(serializers.ModelSerializer):
    # Auparavant depth = 1 : le profil imbriqué renvoyait le code d'accès ASACI en clair à la connexion
    profile = ProfilResumeSerializer(read_only=True)

    class Meta:
        model = UranusUser
        fields = ("id", "email", "is_admin", "name", "profile")


class ProfileSerializer(serializers.ModelSerializer):
    """Profils ASACI des utilisateurs. Le code d'accès est en écriture seule : les réponses indiquent seulement
    s'il est renseigné (code_acces_configure). L'identité et le statut administrateur se gèrent dans
    Administration > Utilisateurs (securite/utilisateurs/), pas ici."""

    utilisateur = serializers.ReadOnlyField(source="utilisateur.id")
    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.CharField(source="utilisateur.email", read_only=True)
    is_admin = serializers.BooleanField(source="utilisateur.is_admin", read_only=True)
    nom = serializers.CharField(source="utilisateur.name", read_only=True)
    code_acces = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True,
                                       max_length=100, style={"input_type": "password"})
    code_acces_configure = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id",
            "email",
            "utilisateur",
            "code_demandeur",
            "code_acces",
            "code_acces_configure",
            "is_admin",
            "nom",
        )

    def get_code_acces_configure(self, obj):
        return bool(obj.code_acces)

    def update(self, instance, validated_data):
        # Seules les données ASACI du profil se modifient ici (l'ancienne version, qui écrivait aussi
        # l'utilisateur, échouait sur instance.user)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={"input_type": "password"}, write_only=True)

    class Meta:
        model = UranusUser
        fields = ("id", "email", "name", "password", "password2")
        extra_kwargs = {"password": {"write_only": True}}

    def save(self):
        user = UranusUser(email=self.validated_data["email"])
        password = self.validated_data["password"]
        password2 = self.validated_data["password2"]
        if password != password2:
            raise serializers.ValidationError(
                {"Password": "Mots de passe non concordants."}
            )
        name = self.validated_data["name"]
        user.set_password(password)
        user.set_name(name)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(label="Email", write_only=True)
    password = serializers.CharField(
        label="Password",
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, data):
        t_user = authenticate(**data)
        if t_user and t_user.is_active:
            return t_user
        raise serializers.ValidationError("Paramètres de connexion invalide.")


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )
    new_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )

    temporary_code = serializers.CharField(required=True)

    def validate_temporary_code(self, value):
        if not check_temporary_code(self.context["request"].user, value):
            raise serializers.ValidationError({"temporary_code": "Code invalide"})
        return value

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError(
                {"current_password": "Mot de passe invalide"}
            )
        return value


###############################################################################
class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )

    user_email = serializers.EmailField(required=True)

    def validate_user_email(self, value):
        t_users = UranusUser.objects.filter(email=value)
        if not t_users.exists():
            raise serializers.ValidationError({"user_email": "Adresse non valide"})
        return value


# Sérialiseurs pour la gestion des dérogations
class DerogationSerializer(serializers.ModelSerializer):
    user_habilite = serializers.ReadOnlyField(source="user_habilite.username")

    class Meta:
        model = Derogation
        fields = [
            "id",
            "user_beneficiaire",
            "user_habilite",
            "date_expiration",
            "motif",
            "date_creation",
            "is_used",
        ]
        read_only_fields = ["id", "user_habilite", "date_creation", "is_used"]


class DerogationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Derogation
        fields = ["user_beneficiaire", "date_expiration", "motif"]


# Sérialiseurs pour la gestion des utilisateurs et des permissions
class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class UserGroupSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=150)
    user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))


class AddPermissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    permission_name = serializers.CharField(max_length=150)
