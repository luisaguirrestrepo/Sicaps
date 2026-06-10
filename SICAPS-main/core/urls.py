from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('registro/', views.registro_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('agenda/', views.agenda_view, name='agenda'),
    path('agenda/crear/', views.crear_cita, name='crear_cita'),
    path('agenda/editar/<str:cita_id>/', views.editar_cita, name='editar_cita'),
    path('agenda/cancelar/<str:cita_id>/', views.cancelar_cita, name='cancelar_cita'),
    path('agenda/eliminar/<str:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('agenda/certificado/<str:cita_id>/', views.generar_certificado, name='certificado'),
    
    path('pacientes/', views.paciente_lista, name='pacientes'),
    path('pacientes/crear/', views.crear_paciente, name='crear_paciente'),
    path('pacientes/editar/<str:paciente_id>/', views.editar_paciente, name='editar_paciente'),
    path('pacientes/toggle/<str:paciente_id>/', views.toggle_paciente_activo, name='toggle_paciente'),
    path('pacientes/eliminar/<str:paciente_id>/', views.eliminar_paciente, name='eliminar_paciente'),
    path('psicologos/crear/', views.crear_psicologo, name='crear_psicologo'),
    path('psicologos/', views.psicologos_list, name='psicologos'),
    path('psicologos/editar/<str:username>/', views.editar_psicologo, name='editar_psicologo'),
    path('psicologos/toggle/<str:username>/', views.toggle_disponibilidad, name='toggle_psicologo'),
    path('psicologos/eliminar/<str:username>/', views.eliminar_psicologo, name='eliminar_psicologo'),
    path('pacientes/<str:paciente_id>/', views.paciente_detalle, name='paciente_detalle'),
    path('pacientes/<str:paciente_id>/nueva-sesion/', views.agregar_sesion, name='agregar_sesion'),
    path('pacientes/<str:paciente_id>/exportar-pdf/', views.exportar_historia_pdf, name='exportar_pdf'),
]
