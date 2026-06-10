from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Crea o actualiza un usuario administrador con permisos completos.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Nombre de usuario del administrador (normalmente correo).')
        parser.add_argument('--email', required=True, help='Correo electrónico del administrador.')
        parser.add_argument('--password', required=True, help='Contraseña del administrador.')
        parser.add_argument('--nombre', default='Administrador', help='Nombre completo del administrador.')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        email = options['email']
        password = options['password']
        nombre = options['nombre']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': nombre,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if not created:
            user.email = email
            user.first_name = nombre
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Administrador actualizado: {username}'))
        else:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Administrador creado: {username}'))

        Group.objects.get_or_create(name='Administrador')
        Group.objects.get_or_create(name='Psicologo')
        Group.objects.get_or_create(name='Paciente')

        grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo_admin)
        self.stdout.write(self.style.SUCCESS('Grupo Administrador asegurado y asignado.'))
