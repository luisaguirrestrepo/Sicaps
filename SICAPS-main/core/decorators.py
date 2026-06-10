from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def es_psicologo(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Psicologo', 'Administrador']).exists()

def psicologo_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is a psychologist,
    raising PermissionDenied if not.
    """
    actual_decorator = user_passes_test(
        es_psicologo,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def es_administrador(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name='Administrador').exists()

def administrador_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is an administrator,
    raising PermissionDenied if not.
    """
    actual_decorator = user_passes_test(
        es_administrador,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def es_admin_o_psicologo(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administrador', 'Psicologo']).exists()
