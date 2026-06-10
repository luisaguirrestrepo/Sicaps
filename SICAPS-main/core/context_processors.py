from datetime import datetime, timedelta
from django.utils import timezone
from .models import Paciente, Cita, HistoriaClinica

def notificaciones_context(request):
    notificaciones = []
    
    if request.user.is_authenticated:
        hoy = timezone.now().date()
        is_staff = request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() or request.user.is_superuser
        
        if is_staff:
            citas_hoy = Cita.objects.filter(fecha=hoy, estado='PROGRAMADA').count()
            if citas_hoy > 0:
                notificaciones.append({
                    'icono': 'fa-solid fa-calendar-check',
                    'color': 'text-blue-500',
                    'bg_color': 'bg-blue-100',
                    'titulo': 'Citas del Día',
                    'mensaje': f'Tienes {citas_hoy} citas programadas para hoy.',
                    'tiempo': 'Hoy'
                })
                
            nuevos_pacientes = Paciente.objects.filter().count() # We could filter by creation date if we had it, fallback to general stats
            if 'Administrador' in request.user.groups.all().values_list('name', flat=True):
                notificaciones.append({
                    'icono': 'fa-solid fa-users',
                    'color': 'text-green-500',
                    'bg_color': 'bg-green-100',
                    'titulo': 'Estado de Pacientes',
                    'mensaje': f'El sistema cuenta con {nuevos_pacientes} pacientes registrados.',
                    'tiempo': 'Sistema'
                })
        else:
            try:
                paciente = Paciente.objects.get(email=request.user.email)
                proxima_cita = Cita.objects.filter(paciente=paciente, fecha__gte=hoy, estado='PROGRAMADA').order_by('fecha', 'hora').first()
                
                if proxima_cita:
                    dias_faltantes = (proxima_cita.fecha - hoy).days
                    if dias_faltantes == 0:
                        mensaje = f"Tu cita es HOY a las {proxima_cita.hora}."
                        color = 'text-red-500'
                        bg_color = 'bg-red-100'
                    elif dias_faltantes == 1:
                        mensaje = f"Recuerda tu cita mañana a las {proxima_cita.hora}."
                        color = 'text-yellow-600'
                        bg_color = 'bg-yellow-100'
                    else:
                        mensaje = f"Tu próxima cita es el {proxima_cita.fecha.strftime('%d/%m/%Y')}."
                        color = 'text-blue-500'
                        bg_color = 'bg-blue-100'
                        
                    notificaciones.append({
                        'icono': 'fa-regular fa-clock',
                        'color': color,
                        'bg_color': bg_color,
                        'titulo': 'Recordatorio de Cita',
                        'mensaje': mensaje,
                        'tiempo': 'Agenda'
                    })
                else:
                    notificaciones.append({
                        'icono': 'fa-solid fa-info-circle',
                        'color': 'text-gray-500',
                        'bg_color': 'bg-gray-100',
                        'titulo': 'Sin citas',
                        'mensaje': 'No tienes citas programadas próximamente.',
                        'tiempo': 'Agenda'
                    })
            except Paciente.DoesNotExist:
                pass
        notificaciones.append({
            'icono': 'fa-solid fa-shield-halved',
            'color': 'text-[var(--color-sura-blue)]',
            'bg_color': 'bg-[var(--color-sura-light)]',
            'titulo': 'Privacidad Activa',
            'mensaje': 'La protección de datos Ley 1581 se encuentra activa.',
            'tiempo': 'Sistema'
        })
                
    return {'notificaciones': notificaciones, 'num_notificaciones': len(notificaciones)}
