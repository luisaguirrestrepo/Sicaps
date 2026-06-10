from datetime import datetime, timedelta
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Paciente, Cita

INPUT_CLASS = 'w-full bg-gray-50 border border-gray-200 text-gray-800 py-2 px-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#00a4e4] transition-all'

class RegistroForm(forms.Form):
    nombre_completo = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))
    confirm_password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))
    documento = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    telefono = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    fecha_nacimiento = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return email.lower()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Las contraseñas no coinciden.')

        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                self.add_error('password', exc)

        return cleaned_data

class PsicologoForm(forms.Form):
    nombre_completo = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    tarjeta_profesional = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))
    confirm_password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return email.lower()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Las contraseñas no coinciden.')

        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                self.add_error('password', exc)

        return cleaned_data

class PacienteForm(forms.Form):
    nombre_completo = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    documento = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    telefono = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    antecedentes_personales = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}))
    antecedentes_familiares = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}))

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        paciente_id = self.initial.get('id', None)

        qs = Paciente.objects.filter(documento=documento)
        if paciente_id:
            qs = qs.filter(id__ne=paciente_id)

        # mongoengine QuerySet doesn't implement .exists(); use .count()
        if qs.count() > 0:
            raise forms.ValidationError('Ya existe un paciente con este documento.')

        return documento


class PsicologoEditForm(forms.Form):
    nombre_completo = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    telefono = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    tarjeta_profesional = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    disponible = forms.BooleanField(required=False)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower()

class CitaForm(forms.Form):
    paciente_id = forms.CharField(max_length=50, required=True)
    fecha = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    hora = forms.CharField(max_length=5, required=True, widget=forms.TimeInput(attrs={'type': 'time'}))
    motivo = forms.CharField(widget=forms.Textarea, required=True)
    estado = forms.ChoiceField(choices=Cita.ESTADOS_CITA, initial='PROGRAMADA', required=False)

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        cita_id = self.initial.get('id', None)  # Useful for updates

        if fecha and hora:
            try:
                hora_obj = datetime.strptime(hora, '%H:%M').time()
            except (ValueError, TypeError):
                self.add_error('hora', 'Formato de hora inválido. Use HH:MM.')
                return cleaned_data

            if hora_obj.minute not in (0, 30):
                self.add_error('hora', 'La hora debe estar en intervalos de 30 minutos (por ejemplo 10:00 o 10:30).')
                return cleaned_data

            citas_existentes = Cita.objects.filter(fecha=fecha, estado__in=['PROGRAMADA', 'COMPLETADA'])
            if cita_id:
                citas_existentes = citas_existentes.filter(id__ne=cita_id)

            for cita in citas_existentes:
                try:
                    existente_obj = datetime.strptime(cita.hora, '%H:%M').time()
                except Exception:
                    continue

                actual_dt = datetime.combine(datetime.today(), hora_obj)
                existente_dt = datetime.combine(datetime.today(), existente_obj)
                diff_minutes = abs((actual_dt - existente_dt).total_seconds()) / 60
                if diff_minutes < 30:
                    self.add_error('hora', 'Ya hay una cita programada muy cercana a este horario. Respeta intervalos de 30 minutos.')
                    break

        return cleaned_data
