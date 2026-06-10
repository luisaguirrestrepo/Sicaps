from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from datetime import timedelta

from .models import Paciente, Cita, HistoriaClinica, SesionClinica
from .forms import CitaForm, PacienteForm, PsicologoForm, RegistroForm, PsicologoEditForm
from .decorators import psicologo_required, es_admin_o_psicologo, administrador_required
from datetime import datetime
@login_required
def dashboard_view(request):
    if not request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() and not request.user.is_superuser:
        return redirect('core:agenda') # Or a specific paciente view. For now, agenda will handle it.
        
    total_pacientes = Paciente.objects.count()
    
    hoy = timezone.now().date()
    
    citas_hoy = Cita.objects.filter(fecha=hoy).count()
    
    citas_crudas = Cita.objects.filter(fecha__gte=hoy).order_by('fecha', 'hora')
    proximas_citas = []
    from mongoengine.errors import DoesNotExist
    for cita in citas_crudas:
        try:
            _ = cita.paciente.nombre_completo
            proximas_citas.append(cita)
            if len(proximas_citas) == 5:
                break
        except DoesNotExist:
            cita.delete()

    context = {
        'total_pacientes': total_pacientes,
        'citas_hoy': citas_hoy,
        'nuevas_historias': HistoriaClinica.objects.filter(fecha_creacion__gte=hoy.replace(day=1)).count(),
        'proximas_citas': proximas_citas
    }
    return render(request, 'core/dashboard.html', context)
@login_required
def agenda_view(request):
    is_psicologo = request.user.groups.filter(name='Psicologo').exists() and not request.user.is_superuser
    is_admin = request.user.groups.filter(name='Administrador').exists() or request.user.is_superuser
    is_staff = is_admin or is_psicologo
    
    filtro = request.GET.get('filtro', 'todos')
    hoy = timezone.now().date()
    from django.contrib.auth.models import User as DjangoUser
    if is_admin:
        psicologos = DjangoUser.objects.filter(groups__name='Psicologo', psicologo_profile__disponible=True)
    elif is_psicologo:
        psicologos = [request.user]
    else:
        psicologos = DjangoUser.objects.filter(groups__name='Psicologo', psicologo_profile__disponible=True)
    if is_staff:
        if is_admin:
            base_query = Cita.objects
        else:
            base_query = Cita.objects.filter(profesional_id=request.user.username)
        pacientes = Paciente.objects.all()
    else:
        try:
            paciente = Paciente.objects.get(email=request.user.email)
            base_query = Cita.objects.filter(paciente=paciente)
            pacientes = [paciente]
        except Paciente.DoesNotExist:
            base_query = Cita.objects.none() # Return empty if no patient
            pacientes = []
    if base_query:
        if filtro == 'hoy':
            citas_crudas = base_query.filter(fecha=hoy).order_by('fecha', 'hora')
        elif filtro == 'semana':
            semana_fin = hoy + timedelta(days=7)
            citas_crudas = base_query.filter(fecha__gte=hoy, fecha__lte=semana_fin).order_by('fecha', 'hora')
        else:
            citas_crudas = base_query.order_by('fecha', 'hora')
            
        citas = []
        from mongoengine.errors import DoesNotExist
        for cita in citas_crudas:
            try:
                _ = cita.paciente.nombre_completo
                citas.append(cita)
            except DoesNotExist:
                cita.delete() # Limpiar citas huerfanas (el paciente fue borrado)
    else:
        citas = []

    context = {
        'citas': citas,
        'pacientes': pacientes,
        'is_staff': is_staff,
        'is_psicologo': is_psicologo,
        'psicologos': psicologos
    }
    return render(request, 'core/agenda.html', context)

@login_required
def crear_cita(request):
    if request.method == 'POST':
        is_psicologo = request.user.groups.filter(name='Psicologo').exists() and not request.user.is_superuser
        is_staff = request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() or request.user.is_superuser
        
        if is_staff:
            paciente_id = request.POST.get('paciente_id')
            if not paciente_id:
                messages.error(request, "Debe seleccionar un paciente.")
                return redirect('core:agenda')
            paciente = Paciente.objects.get(id=paciente_id)
        else:
            try:
                paciente = Paciente.objects.get(email=request.user.email)
            except Paciente.DoesNotExist:
                messages.error(request, "Error de perfil de paciente.")
                return redirect('core:agenda')
                
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        motivo = request.POST.get('motivo')
        if is_psicologo:
            psicologo_username = request.user.username
        else:
            psicologo_username = request.POST.get('psicologo_username') or None
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            if fecha_obj < timezone.now().date():
                 messages.error(request, 'No puedes agendar citas en fechas pasadas.')
                 return redirect('core:agenda')
        except:
             messages.error(request, 'Fecha inválida para la cita.')
             return redirect('core:agenda')

        try:
            hora_obj = datetime.strptime(hora, '%H:%M').time()
        except Exception:
            messages.error(request, 'Formato de hora inválido.')
            return redirect('core:agenda')

        if hora_obj.minute not in (0, 30):
            messages.error(request, 'Selecciona una hora en intervalos de 30 minutos.')
            return redirect('core:agenda')

        hora = hora_obj.strftime('%H:%M')

        conflict_exists = False
        citas_misma_fecha = Cita.objects.filter(fecha=fecha_obj, estado__in=['PROGRAMADA', 'COMPLETADA'])
        for cita_existente in citas_misma_fecha:
            try:
                existente_obj = datetime.strptime(cita_existente.hora, '%H:%M').time()
            except Exception:
                continue
            actual_dt = datetime.combine(datetime.today(), hora_obj)
            existente_dt = datetime.combine(datetime.today(), existente_obj)
            if abs((actual_dt - existente_dt).total_seconds()) / 60 < 30:
                conflict_exists = True
                break

        if conflict_exists:
            messages.error(request, 'Ya hay una cita programada muy cercana a este horario. Respeta intervalos de 30 minutos.')
            return redirect('core:agenda')

        overlap = Cita.objects.filter(fecha=fecha_obj, hora=hora, estado__in=['PROGRAMADA', 'COMPLETADA']).count()
        if overlap > 0:
            messages.error(request, 'El espacio ya está ocupado en la agenda. Por favor, selecciona otra hora u otra fecha.')
            return redirect('core:agenda')

        # Si se asignó un psicólogo, comprobar disponibilidad específica
        if psicologo_username:
            from django.contrib.auth.models import User as DjangoUser
            try:
                psicologo_user = DjangoUser.objects.get(username=psicologo_username, groups__name='Psicologo')
            except DjangoUser.DoesNotExist:
                messages.error(request, 'Psicólogo seleccionado no válido.')
                return redirect('core:agenda')

            try:
                perfil = psicologo_user.psicologo_profile
            except Exception:
                perfil = None
            if perfil is None or not perfil.disponible:
                messages.error(request, 'El psicólogo seleccionado no está disponible.')
                return redirect('core:agenda')

            overlap_prof = Cita.objects.filter(fecha=fecha_obj, hora=hora, profesional_id=psicologo_username, estado__in=['PROGRAMADA', 'COMPLETADA']).count()
            if overlap_prof > 0:
                messages.error(request, 'El psicólogo seleccionado no está disponible en esa hora. Elige otro.')
                return redirect('core:agenda')

        nueva_cita = Cita(
            paciente=paciente,
            fecha=fecha_obj,
            hora=hora,
            profesional_id=psicologo_username,
            motivo=motivo,
            estado='PROGRAMADA'
        )
        nueva_cita.save()
        
        messages.success(request, f'Cita agendada correctamente. Se ha enviado una notificación al correo de {paciente.nombre_completo}.')
    return redirect('core:agenda')

@login_required
@user_passes_test(es_admin_o_psicologo)
def editar_cita(request, cita_id):
    cita = Cita.objects.get(id=cita_id)
    if request.method == 'POST':
        form = CitaForm(request.POST, initial={'id': cita_id})
        if form.is_valid():
            paciente_id = form.cleaned_data['paciente_id']
            paciente = Paciente.objects.get(id=paciente_id)
            
            cita.paciente = paciente
            cita.fecha = form.cleaned_data['fecha']
            cita.hora = form.cleaned_data['hora']
            cita.motivo = form.cleaned_data['motivo']
            cita.estado = form.cleaned_data.get('estado', cita.estado)
            cita.save()
            messages.success(request, 'Cita actualizada correctamente.')
            return redirect('core:agenda')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect('core:agenda')

@login_required
def cancelar_cita(request, cita_id):
    if request.method == 'POST':
        cita = Cita.objects.get(id=cita_id)
        
        is_staff = request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() or request.user.is_superuser
        
        if not is_staff:
            hoy = timezone.now().date()
            if (cita.fecha - hoy).days <= 1:
                messages.error(request, 'No puedes cancelar citas con menos de 24 horas de antelación. Por favor comunícate directamente con la clínica.')
                return redirect('core:agenda')
                
        cita.estado = 'CANCELADA'
        cita.save()
        
        messages.success(request, f'Cita cancelada correctamente. Se ha enviado una notificación al correo de {cita.paciente.nombre_completo}.')
    return redirect('core:agenda')

@login_required
@user_passes_test(es_admin_o_psicologo)
def eliminar_cita(request, cita_id):
    if request.method == 'POST':
        try:
            cita = Cita.objects.get(id=cita_id)
            cita.delete()
            messages.success(request, 'El registro de la cita ha sido eliminado permanentemente del historial.')
        except Cita.DoesNotExist:
            messages.error(request, 'La cita no existe.')
    referer = request.META.get('HTTP_REFERER', '')
    if 'agenda' in referer:
        return redirect('core:agenda')
    return redirect('core:dashboard')

@login_required
def generar_certificado(request, cita_id):
    cita = Cita.objects.get(id=cita_id)
    is_staff = request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() or request.user.is_superuser
    if not is_staff and cita.paciente.email != request.user.email:
        messages.error(request, 'No tienes permiso para ver este documento.')
        return redirect('core:agenda')
        
    if cita.estado != 'COMPLETADA':
        messages.error(request, 'El certificado solo se puede generar para citas completadas.')
        return redirect('core:agenda')
        
    return render(request, 'core/certificado.html', {'cita': cita})

@login_required
def perfil_view(request):
    paciente = Paciente.objects.filter(email__iexact=request.user.email).first()
    
    if request.method == 'POST':
        telefono = request.POST.get('telefono', '')
        nombre = request.POST.get('nombre_completo', '')

        request.user.first_name = nombre
        request.user.save()

        if not paciente:
            paciente = Paciente(
                nombre_completo=nombre,
                documento=request.POST.get('documento', ''),
                telefono=telefono,
                email=request.user.email
            )
        else:
            paciente.telefono = telefono
            paciente.nombre_completo = nombre

        paciente.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('core:perfil')

    return render(request, 'core/perfil.html', {'paciente': paciente})
@login_required
@user_passes_test(es_admin_o_psicologo)
def paciente_lista(request):
    from mongoengine import Q
    query = request.GET.get('q', '')
    if query:
        pacientes = Paciente.objects.filter(
            Q(nombre_completo__icontains=query) | 
            Q(documento__icontains=query) | 
            Q(email__icontains=query)
        )
    else:
        pacientes = Paciente.objects.all()

    for paciente in pacientes:
        if getattr(paciente, 'activo', None) is None:
            paciente.activo = True

    form = PacienteForm()
    return render(request, 'core/paciente_lista.html', {
        'pacientes': pacientes,
        'form': form,
        'query': query,
        'is_superuser': request.user.is_superuser,
    })

@login_required
def toggle_paciente_activo(request, paciente_id):
    if not request.user.is_superuser:
        messages.error(request, 'No tiene permiso para modificar el estado de pacientes.')
        return redirect('core:pacientes')

    if request.method == 'POST':
        paciente = Paciente.objects.get(id=paciente_id)
        paciente.activo = not getattr(paciente, 'activo', True)
        paciente.save()
        if paciente.activo:
            messages.success(request, 'Paciente activado correctamente.')
        else:
            messages.success(request, 'Paciente desactivado correctamente.')
    return redirect('core:pacientes')

@login_required
@user_passes_test(es_admin_o_psicologo)
def crear_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            nuevo_paciente = Paciente(
                nombre_completo=form.cleaned_data['nombre_completo'],
                documento=form.cleaned_data['documento'],
                telefono=form.cleaned_data['telefono'],
                email=form.cleaned_data['email'],
                antecedentes_personales=form.cleaned_data.get('antecedentes_personales', ''),
                antecedentes_familiares=form.cleaned_data.get('antecedentes_familiares', '')
            )
            nuevo_paciente.save()
            messages.success(request, 'Paciente registrado correctamente.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect('core:pacientes')

@login_required
@administrador_required
def crear_psicologo(request):
    if request.method == 'POST':
        form = PsicologoForm(request.POST)
        if form.is_valid():
            nombre_completo = form.cleaned_data['nombre_completo']
            email = form.cleaned_data['email']
            tarjeta_profesional = form.cleaned_data['tarjeta_profesional']
            password = form.cleaned_data['password']

            if User.objects.filter(username__iexact=email).exists():
                messages.error(request, 'Ya existe una cuenta con este correo.')
                return redirect('core:crear_psicologo')

            try:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=nombre_completo,
                    is_staff=True
                )
                user.save()
                grupo, _ = Group.objects.get_or_create(name='Psicologo')
                user.groups.add(grupo)
                # Asegurar perfil de psicólogo
                try:
                    from .models import PsicologoProfile
                    perfil, _ = PsicologoProfile.objects.get_or_create(user=user)
                    perfil.telefono = ''
                    perfil.tarjeta_profesional = tarjeta_profesional
                    perfil.save()
                except Exception:
                    pass

                messages.success(request, f'Psicólogo {nombre_completo} creado correctamente.')
                return redirect('core:dashboard')
            except Exception as e:
                messages.error(request, f'Error al crear el psicólogo: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PsicologoForm()

    return render(request, 'core/crear_psicologo.html', {'form': form})


@login_required
@administrador_required
def psicologos_list(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if request.method == 'POST':
        form = PsicologoForm(request.POST)
        if form.is_valid():
            nombre_completo = form.cleaned_data['nombre_completo']
            email = form.cleaned_data['email']
            tarjeta_profesional = form.cleaned_data['tarjeta_profesional']
            password = form.cleaned_data['password']

            try:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=nombre_completo,
                    is_staff=True
                )
                user.save()
                grupo, _ = Group.objects.get_or_create(name='Psicologo')
                user.groups.add(grupo)
                from .models import PsicologoProfile
                perfil, _ = PsicologoProfile.objects.get_or_create(user=user)
                perfil.telefono = ''
                perfil.tarjeta_profesional = tarjeta_profesional
                perfil.disponible = True
                perfil.save()
                messages.success(request, f'Psicólogo {nombre_completo} creado correctamente.')
                return redirect('core:psicologos')
            except Exception as e:
                messages.error(request, f'Error al crear el psicólogo: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PsicologoForm()

    psicologos = User.objects.filter(groups__name='Psicologo')
    psicologos_data = []
    from .models import PsicologoProfile
    for p in psicologos:
        try:
            perfil = PsicologoProfile.objects.filter(user=p).first()
        except Exception:
            perfil = None
        psicologos_data.append({'user': p, 'perfil': perfil})

    return render(request, 'core/psicologos_list.html', {'psicologos_data': psicologos_data, 'form': form})


@login_required
@administrador_required
def editar_psicologo(request, username):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, 'Psicólogo no encontrado.')
        return redirect('core:psicologos')

    from .models import PsicologoProfile
    perfil, _ = PsicologoProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = PsicologoEditForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['nombre_completo']
            user.email = form.cleaned_data['email']
            user.save()

            perfil.telefono = form.cleaned_data.get('telefono', '')
            perfil.tarjeta_profesional = form.cleaned_data.get('tarjeta_profesional', '')
            perfil.disponible = bool(form.cleaned_data.get('disponible', False))
            perfil.save()
            messages.success(request, 'Datos del psicólogo actualizados.')
            return redirect('core:psicologos')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        initial = {
            'nombre_completo': user.first_name,
            'email': user.email,
            'telefono': perfil.telefono,
            'tarjeta_profesional': perfil.tarjeta_profesional,
            'disponible': perfil.disponible
        }
        form = PsicologoEditForm(initial=initial)

    return render(request, 'core/psicologo_edit.html', {'form': form, 'user_obj': user, 'perfil': perfil})


@login_required
@administrador_required
def toggle_disponibilidad(request, username):
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            from .models import PsicologoProfile
            perfil, _ = PsicologoProfile.objects.get_or_create(user=user)
            perfil.disponible = not perfil.disponible
            perfil.save()
            messages.success(request, f"Disponibilidad actualizada: {'Disponible' if perfil.disponible else 'No disponible'}")
        except User.DoesNotExist:
            messages.error(request, 'Psicólogo no encontrado.')
    return redirect('core:psicologos')


@login_required
@administrador_required
def eliminar_psicologo(request, username):
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            if user.is_superuser:
                messages.error(request, 'No puedes eliminar a un superusuario.')
            else:
                user.delete()
                messages.success(request, 'Psicólogo eliminado.')
        except User.DoesNotExist:
            messages.error(request, 'Psicólogo no encontrado.')
    return redirect('core:psicologos')

@login_required
@user_passes_test(es_admin_o_psicologo)
def editar_paciente(request, paciente_id):
    paciente = Paciente.objects.get(id=paciente_id)
    if request.method == 'POST':
        form = PacienteForm(request.POST, initial={'id': paciente_id})
        if form.is_valid():
            is_psicologo = request.user.groups.filter(name='Psicologo').exists() and not request.user.is_superuser
            if not is_psicologo:
                paciente.nombre_completo = form.cleaned_data['nombre_completo']
                paciente.documento = form.cleaned_data['documento']
            paciente.telefono = form.cleaned_data['telefono']
            paciente.email = form.cleaned_data['email']
            paciente.antecedentes_personales = form.cleaned_data.get('antecedentes_personales', '')
            paciente.antecedentes_familiares = form.cleaned_data.get('antecedentes_familiares', '')
            paciente.save()
            messages.success(request, 'Datos del paciente actualizados.')
            return redirect('core:paciente_detalle', paciente_id=paciente.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('core:paciente_detalle', paciente_id=paciente.id)
    return redirect('core:pacientes')

@login_required
@user_passes_test(es_admin_o_psicologo)
def eliminar_paciente(request, paciente_id):
    if request.method == 'POST':
        paciente = Paciente.objects.get(id=paciente_id)
        
        # Eliminar también el usuario asociado en SQLite para evitar bloqueos futuros de registro
        try:
            from django.contrib.auth.models import User
            user_asociado = User.objects.filter(username=paciente.email).first()
            if user_asociado and not user_asociado.is_superuser:
                user_asociado.delete()
        except:
            pass
            
        paciente.delete()
        messages.success(request, 'Paciente eliminado correctamente.')
    return redirect('core:pacientes')
@login_required
@psicologo_required
def paciente_detalle(request, paciente_id):
    paciente = Paciente.objects.get(id=paciente_id)
    from mongoengine.errors import FieldDoesNotExist
    try:
        historia = HistoriaClinica.objects.get(paciente=paciente)
    except FieldDoesNotExist:
        # Migrar sesiones antiguas con campos obsoletos a la nueva estructura
        coll = HistoriaClinica._get_collection()
        raw = coll.find_one({'paciente': paciente.id})
        if raw and 'sesiones' in raw:
            nuevas = []
            for s in raw.get('sesiones', []):
                # Mapear campos antiguos a nuevos con valores por defecto
                fecha = s.get('fecha_sesion') or s.get('fecha_registro') or datetime.now()
                if isinstance(fecha, str):
                    try:
                        fecha = datetime.fromisoformat(fecha)
                    except Exception:
                        fecha = datetime.now()
                nueva = {
                    'codigo_diagnostico': s.get('diagnostico') or '',
                    'nombre': s.get('diagnostico') or s.get('motivo_consulta') or '',
                    'descripcion': s.get('observaciones') or '',
                    'fecha_registro': fecha,
                    'profesional_responsable': s.get('profesional_id') or s.get('profesional_responsable') or '',
                    'observaciones_clinicas': s.get('observaciones') or s.get('observaciones_clinicas') or '',
                    'nivel_riesgo': s.get('nivel_riesgo') or 'Bajo',
                    'estado_paciente': s.get('estado_paciente') or 'Estable'
                }
                nuevas.append(nueva)
            coll.update_one({'_id': raw['_id']}, {'$set': {'sesiones': nuevas}})
        try:
            historia = HistoriaClinica.objects.get(paciente=paciente)
        except HistoriaClinica.DoesNotExist:
            historia = HistoriaClinica(
                paciente=paciente,
                fecha_creacion=datetime.now(),
                fecha_ultima_modificacion=datetime.now(),
                sesiones=[]
            )
            historia.save()
    except HistoriaClinica.DoesNotExist:
        historia = HistoriaClinica(
            paciente=paciente,
            fecha_creacion=datetime.now(),
            fecha_ultima_modificacion=datetime.now(),
            sesiones=[]
        )
        historia.save()
    # pasar diagnósticos para autocompletar en la plantilla
    from .models import DIAGNOSTICOS
    import json
    is_psicologo = request.user.groups.filter(name='Psicologo').exists() and not request.user.is_superuser
    context = {
        'paciente': paciente,
        'historia': historia,
        'diagnosticos_json': json.dumps(DIAGNOSTICOS),
        'is_psicologo': is_psicologo,
    }
    return render(request, 'core/paciente_detalle.html', context)

@login_required
@psicologo_required
def agregar_sesion(request, paciente_id):
    if request.method == 'POST':
        paciente = Paciente.objects.get(id=paciente_id)
        historia = HistoriaClinica.objects.get(paciente=paciente)
        codigo = request.POST.get('codigo_diagnostico')
        nombre = request.POST.get('nombre_diagnostico')
        descripcion = request.POST.get('descripcion_diagnostico')
        observaciones = request.POST.get('observaciones_clinicas')
        nivel_riesgo = request.POST.get('nivel_riesgo')
        estado_paciente = request.POST.get('estado_paciente')

        nueva_sesion = SesionClinica(
            codigo_diagnostico=codigo,
            nombre=nombre,
            descripcion=descripcion,
            fecha_registro=datetime.now(),
            profesional_responsable=request.user.get_full_name() or request.user.username,
            observaciones_clinicas=observaciones,
            nivel_riesgo=nivel_riesgo,
            estado_paciente=estado_paciente
        )
        
        historia.sesiones.append(nueva_sesion)
        historia.fecha_ultima_modificacion = datetime.now()
        historia.save()
        messages.success(request, 'Sesión clínica agregada correctamente.')
    return redirect('core:paciente_detalle', paciente_id=paciente_id)

@login_required
def exportar_historia_pdf(request, paciente_id):
    paciente = Paciente.objects.get(id=paciente_id)
    is_staff = request.user.groups.filter(name__in=['Administrador', 'Psicologo']).exists() or request.user.is_superuser
    if not is_staff and request.user.email != paciente.email:
        messages.error(request, 'No tienes permiso para exportar este historial.')
        return redirect('core:perfil')

    try:
        historia = HistoriaClinica.objects.get(paciente=paciente)
    except HistoriaClinica.DoesNotExist:
        historia = HistoriaClinica(
            paciente=paciente,
            fecha_creacion=datetime.now(),
            fecha_ultima_modificacion=datetime.now(),
            sesiones=[]
        )
        historia.save()

    resumen = historia.exportar_resumen()
    return render(request, 'core/historia_pdf.html', {'resumen': resumen, 'paciente': paciente})
def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            nombre_completo = form.cleaned_data['nombre_completo']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            telefono = form.cleaned_data['telefono']
            documento = form.cleaned_data['documento']
            rol = 'Paciente'

            try:
                # Crear el usuario
                user = User.objects.create_user(
                    username=email, 
                    email=email, 
                    password=password, 
                    first_name=nombre_completo
                )
                user.save()
                
                # Asignar grupo - usar try/except para evitar problemas de mongoengine
                try:
                    grupo = Group.objects.get(name=rol)
                except Group.DoesNotExist:
                    grupo = Group.objects.create(name=rol)
                user.groups.add(grupo)

                # Si es paciente, crear registro en MongoDB
                if rol == 'Paciente':
                    try:
                        paciente = Paciente.objects.get(email=email)
                        paciente.nombre_completo = nombre_completo
                        paciente.documento = documento
                        paciente.telefono = telefono
                        paciente.fecha_nacimiento = form.cleaned_data.get('fecha_nacimiento')
                        paciente.save()
                    except Paciente.DoesNotExist:
                        paciente = Paciente(
                            nombre_completo=nombre_completo,
                            documento=documento,
                            telefono=telefono,
                            email=email,
                            fecha_nacimiento=form.cleaned_data.get('fecha_nacimiento')
                        )
                        paciente.save()

                # Autenticar e iniciar sesión
                user = authenticate(request, username=email, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Cuenta creada exitosamente como {rol}. ¡Bienvenido!')
                    return redirect('core:dashboard')
                else:
                    # Si no se autentica, mostrar mensaje pero permitir login manual
                    messages.warning(request, 'Cuenta creada exitosamente. Por favor, inicie sesión con sus credenciales.')
                    return redirect('login')
            except Exception as e:
                messages.error(request, f'Error al crear la cuenta: {str(e)}')
                return redirect('core:registro')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegistroForm()

    return render(request, 'registration/registro.html', {'form': form})

