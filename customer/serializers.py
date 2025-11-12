from rest_framework import serializers
from .models import Client
from configuration_api.models import TypeAssure, TypeSouscripteur, Qualite, Profession, SecteurActivite


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            profession = Profession.objects.get(pk=instance.IdProfession)
            representation["libelleprofession"] = profession.Libelle
            qualite = Qualite.objects.get(pk=instance.IdQualite)
            representation["civilite"] = qualite.Libelle
        except Profession.DoesNotExist as error:
            print(error)
        except Qualite.DoesNotExist as error:
            print(error)
        finally:
            return representation
