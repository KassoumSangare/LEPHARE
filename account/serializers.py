from django.contrib.auth import authenticate
from .models import UranusUser, Profile
from .utils import check_temporary_code
from rest_framework import serializers
from django.contrib.auth.models import Group
from .models import Derogation

User = UranusUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UranusUser
        depth = 1
        fields = ("id", "email", "is_admin", "name", "profile")


class ProfileSerializer(serializers.ModelSerializer):
    
    utilisateur = serializers.ReadOnlyField(source="utilisateur.id")
    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.CharField(source="utilisateur.email")

    class Meta:
        model = Profile
        depth = 1
        fields = (
            "id",
            "email",
            "utilisateur",
            "code_demandeur",
            "code_acces",
        )

    def update(self, instance, validated_data):
        # retrieve the User
        user_data = validated_data.pop("utilisateur", None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)

        # retrieve Profile
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.user.save()
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
