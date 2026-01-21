# commissions/tests/factories/base_factories.py

"""
Factories pour les modèles de base (User, etc.)
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(DjangoModelFactory):
    """Factory pour créer des utilisateurs de test"""
    
    class Meta:
        model = User
        django_get_or_create = ('username',)
    
    name = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.name.strip()}@test.com')
    is_active = True
    is_admin = False
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)
        else:
            self.set_password('testpass123')