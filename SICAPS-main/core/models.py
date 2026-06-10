from mongoengine import Document, StringField, DateTimeField, ReferenceField, DateField, BooleanField

class Paciente(Document):
    nombre_completo = StringField(required=True, max_length=200)
    documento = StringField(required=True, max_length=20, unique=True)
    telefono = StringField(max_length=20)
    email = StringField(max_length=100)
    fecha_nacimiento = DateField()
    antecedentes_personales = StringField()
    antecedentes_familiares = StringField()
    activo = BooleanField(default=True)
    
    meta = {'collection': 'pacientes'}

    def __str__(self):
        return self.nombre_completo

class Cita(Document):
    ESTADOS_CITA = (
        ('PROGRAMADA', 'Programada'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    )

    paciente = ReferenceField(Paciente, required=True)
    fecha = DateField(required=True)
    hora = StringField(required=True, max_length=5) # Format HH:MM
    profesional_id = StringField(required=False, max_length=200)  # username/id del psicólogo asignado
    estado = StringField(choices=ESTADOS_CITA, default='PROGRAMADA')
    motivo = StringField(required=True, max_length=500)
    
    meta = {
        'collection': 'citas',
        'indexes': [
            {'fields': ('fecha', 'hora'), 'unique': False}
        ]
    }

    def __str__(self):
        return f"{self.fecha} {self.hora} - {self.paciente.nombre_completo}"

from mongoengine import EmbeddedDocument, ListField, EmbeddedDocumentField, EmbeddedDocumentListField
from django.db import models as dj_models
from django.contrib.auth import get_user_model

# Perfil para psicólogos (almacenado en SQLite junto al User de Django)
User = get_user_model()

class PsicologoProfile(dj_models.Model):
    user = dj_models.OneToOneField(User, on_delete=dj_models.CASCADE, related_name='psicologo_profile')
    telefono = dj_models.CharField(max_length=50, blank=True)
    tarjeta_profesional = dj_models.CharField(max_length=100, blank=True)
    disponible = dj_models.BooleanField(default=True)
    bio = dj_models.TextField(blank=True)

    def __str__(self):
        return f"Perfil Psicólogo - {self.user.get_full_name() or self.user.username}"

# Diccionario de códigos diagnósticos: código -> nombre, descripción
DIAGNOSTICOS = {
    'DP-01': {'nombre': 'Trastorno de ansiedad generalizada', 'descripcion': 'Presencia constante de preocupación y ansiedad excesiva.'},
    'DP-02': {'nombre': 'Trastorno depresivo', 'descripcion': 'Alteraciones persistentes del estado de ánimo y pérdida de interés.'},
    'DP-03': {'nombre': 'Estrés laboral', 'descripcion': 'Afectación emocional relacionada con presión o sobrecarga laboral.'},
    'DP-04': {'nombre': 'Estrés académico', 'descripcion': 'Dificultades emocionales derivadas del entorno educativo.'},
    'DP-05': {'nombre': 'Trastorno de pánico', 'descripcion': 'Episodios repentinos de miedo intenso y síntomas físicos asociados.'},
    'DP-06': {'nombre': 'Trastorno obsesivo compulsivo', 'descripcion': 'Pensamientos recurrentes y conductas repetitivas compulsiva.'},
    'DP-07': {'nombre': 'Trastorno de adaptación', 'descripcion': 'Respuesta emocional o conductual ante cambios o situaciones difíciles.'},
    'DP-08': {'nombre': 'Problemas de autoestima', 'descripcion': 'Alteraciones relacionadas con la percepción negativa personal.'},
    'DP-09': {'nombre': 'Dificultades familiares', 'descripcion': 'Conflictos emocionales asociados al entorno familiar.'},
    'DP-10': {'nombre': 'Dificultades de pareja', 'descripcion': 'Problemas emocionales y comunicativos en relaciones afectivas.'},
    'DP-11': {'nombre': 'Duelo emocional', 'descripcion': 'Proceso psicológico asociado a pérdidas significativas.'},
    'DP-12': {'nombre': 'Trastorno de conducta', 'descripcion': 'Alteraciones comportamentales persistentes.'},
    'DP-13': {'nombre': 'Déficit de atención e hiperactividad (TDAH)', 'descripcion': 'Dificultades de atención, impulsividad e hiperactividad.'},
    'DP-14': {'nombre': 'Trastorno del sueño', 'descripcion': 'Alteraciones psicológicas relacionadas con el descanso.'},
    'DP-15': {'nombre': 'Dependencia emocional', 'descripcion': 'Necesidad excesiva de validación afectiva.'},
    'DP-16': {'nombre': 'Burnout', 'descripcion': 'Agotamiento físico y emocional relacionado con actividades laborales.'},
    'DP-17': {'nombre': 'Trastorno bipolar', 'descripcion': 'Alteraciones extremas del estado de ánimo.'},
    'DP-18': {'nombre': 'Trastornos alimenticios', 'descripcion': 'Conductas alteradas relacionadas con alimentación e imagen corporal.'},
    'DP-19': {'nombre': 'Fobia específica', 'descripcion': 'Miedo intenso e irracional hacia situaciones u objetos concretos.'},
    'DP-20': {'nombre': 'Problemas de regulación emocional', 'descripcion': 'Dificultades para controlar emociones y respuestas conductuales.'},
}

class SesionClinica(EmbeddedDocument):
    codigo_diagnostico = StringField(max_length=20)
    nombre = StringField(max_length=500)
    descripcion = StringField()
    fecha_registro = DateTimeField(required=True)
    profesional_responsable = StringField()
    observaciones_clinicas = StringField()
    nivel_riesgo = StringField()
    estado_paciente = StringField()

class HistoriaClinica(Document):
    paciente = ReferenceField(Paciente, required=True, unique=True)
    fecha_creacion = DateTimeField(required=True)
    fecha_ultima_modificacion = DateTimeField(required=True)
    sesiones = EmbeddedDocumentListField(SesionClinica)
    
    meta = {
        'collection': 'historias_clinicas',
        'indexes': ['paciente']
    }

    def __str__(self):
        return f"Historia Clínica - {self.paciente.nombre_completo}"

    def exportar_resumen(self):
        resumen = {
            'paciente': self.paciente.nombre_completo,
            'documento': self.paciente.documento,
            'fecha_apertura': self.fecha_creacion.strftime('%Y-%m-%d'),
            'total_sesiones': len(self.sesiones),
            'sesiones': []
        }
        for s in self.sesiones:
            resumen['sesiones'].append({
                'fecha': s.fecha_registro.strftime('%Y-%m-%d %H:%M'),
                'codigo': getattr(s, 'codigo_diagnostico', ''),
                'nombre': getattr(s, 'nombre', ''),
                'descripcion': getattr(s, 'descripcion', ''),
                'profesional': getattr(s, 'profesional_responsable', ''),
                'observaciones': getattr(s, 'observaciones_clinicas', ''),
                'nivel_riesgo': getattr(s, 'nivel_riesgo', ''),
                'estado_paciente': getattr(s, 'estado_paciente', ''),
            })
        return resumen
