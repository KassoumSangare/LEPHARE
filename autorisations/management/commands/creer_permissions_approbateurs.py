# management/commands/creer_permissions_approbateurs.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from autorisations.models import Permission, TypeOperation

User = get_user_model()


class Command(BaseCommand):
    help = 'Crée les permissions pour les approbateurs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email de l\'utilisateur',
            required=True
        )
        parser.add_argument(
            '--type-operation',
            type=str,
            choices=[choice[0] for choice in TypeOperation.choices],
            help='Type d\'opération à autoriser',
            required=True
        )

    def handle(self, *args, **options):
        email = options['email']
        type_op = options['type_operation']
        
        try:
            user = User.objects.get(email=email)
            
            permission, created = Permission.objects.get_or_create(
                utilisateur=user,
                type_operation=type_op,
                defaults={'actif': True}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Permission créée pour {user.email} - {type_op}'
                    )
                )
            else:
                if not permission.actif:
                    permission.actif = True
                    permission.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Permission réactivée pour {user.email} - {type_op}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Permission existe déjà pour {user.email} - {type_op}'
                        )
                    )
        
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Utilisateur {email} introuvable')
            )


# Utilisation:
# python manage.py creer_permissions_approbateurs --email ouattara --type-operation ANNUL_ENC
