# SICAPS

Sistema de información clínica para gestión de psicólogos y pacientes.

## Requisitos

- Python 3.11+ o 3.10
- MongoDB local o remoto (`mongodb://localhost:27017/sicaps_db` por defecto)
- Git (opcional)

## Instalación local

1. Crear y activar el entorno virtual:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
2. Instalar dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
3. Asegurar que MongoDB esté en ejecución.
4. Ejecutar migraciones:
   ```powershell
   python manage.py migrate
   ```
5. Crear usuario administrador:
   ```powershell
   python manage.py createsuperuser
   ```
6. Ejecutar la aplicación:
   ```powershell
   python manage.py runserver
   ```

La aplicación estará disponible en `http://127.0.0.1:8000/`.

## Variables de entorno

- `DJANGO_SECRET_KEY`: clave secreta Django.
- `DJANGO_DEBUG`: `False` en producción.
- `DJANGO_ALLOWED_HOSTS`: hosts permitidos separados por comas.
- `MONGO_HOST`: URL de conexión de MongoDB. Por ejemplo:
  `mongodb://usuario:contraseña@host:27017/sicaps_db`

## Subir a GitHub

Si tu repositorio es `https://github.com/luisaguirrestrepo/Sicaps`, ejecuta:

```powershell
cd "c:\Users\luisa\Documents\Trabajo de grados\SICAPS-main"
git init
git add .
git commit -m "Subir SICAPS a GitHub"
git branch -M main
git remote add origin https://github.com/luisaguirrestrepo/Sicaps.git
git push -u origin main
```

Si ya tienes GitHub instalado y el repositorio ya existe, usa `git pull --rebase origin main` antes de empujar para evitar conflictos.

## Despliegue

Para desplegar en un proveedor como Render, Railway o similar:

1. Configurar el repositorio.
2. Usar `python -m pip install -r requirements.txt`.
3. Configurar las variables de entorno del servicio.
4. Ejecutar el comando de inicio:
   ```text
   web: gunicorn sicaps.wsgi --log-file -
   ```

### Nota

El proyecto usa SQLite para la configuración Django local y MongoDB para los datos principales. En producción se recomienda provisionar un MongoDB gestionado y conectar con `MONGO_HOST`.

## Publicación temporal para pruebas

Si necesitas un acceso de prueba rápido desde un equipo local, puedes usar `ngrok` para exponer el servidor local con una URL pública.
