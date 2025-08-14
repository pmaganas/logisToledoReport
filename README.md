# Sesame Report Generator

Sistema de generación de reportes integrado con la API de Sesame Time Tracking para la gestión y análisis de registros de tiempo de empleados.

## Características Principales

- 📊 Generación de reportes en formato Excel (XLSX) y CSV
- 🔄 Procesamiento en segundo plano con indicadores de progreso en tiempo real
- 🔐 Autenticación segura con gestión de tokens API
- 💾 Persistencia de datos en PostgreSQL
- 🌍 Soporte multi-región para la API de Sesame
- 📱 Interfaz responsive con Tailwind CSS
- ⚡ Eliminación automática de pausas y consolidación de registros

## Requisitos Previos

- Docker y Docker Compose
- Cuenta en Sesame Time con acceso API
- Puerto 5000 disponible (configurable)

## Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd sesame-report-generator
```

### 2. Configuración de Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# Credenciales de Administrador (requeridas)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=tu_password_seguro

# Configuración de Base de Datos (PostgreSQL)
POSTGRES_DB=sesame_reports
POSTGRES_USER=sesame_user
POSTGRES_PASSWORD=password_seguro_db
DATABASE_URL=postgresql://sesame_user:password_seguro_db@db:5432/sesame_reports

# Configuración de Flask
FLASK_SECRET_KEY=clave_secreta_aleatoria_muy_larga
SESSION_SECRET=otra_clave_secreta_aleatoria

# Puerto de la Aplicación (opcional, default: 5000)
PORT=5000

# Configuración de Workers (opcional)
WEB_CONCURRENCY=4
```

### 3. Crear el Dockerfile

Crear un archivo `Dockerfile` en la raíz del proyecto:

```dockerfile
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requerimientos
COPY pyproject.toml ./
COPY requirements.txt ./

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p temp_reports logs

# Exponer el puerto
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--reload", "main:app"]
```

### 4. Crear requirements.txt

Crear un archivo `requirements.txt` con las dependencias:

```txt
Flask==3.0.3
flask-sqlalchemy==3.1.1
psycopg2-binary==2.9.9
gunicorn==23.0.0
requests==2.32.3
openpyxl==3.1.5
python-dateutil==2.9.0
email-validator==2.2.0
cryptography==43.0.0
```

### 5. Crear Docker Compose

Crear un archivo `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: sesame_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - sesame_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    container_name: sesame_app
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ADMIN_USERNAME: ${ADMIN_USERNAME}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      FLASK_SECRET_KEY: ${FLASK_SECRET_KEY}
      SESSION_SECRET: ${SESSION_SECRET}
      WEB_CONCURRENCY: ${WEB_CONCURRENCY:-4}
    ports:
      - "${PORT:-5000}:5000"
    volumes:
      - ./temp_reports:/app/temp_reports
      - ./logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
    networks:
      - sesame_network
    restart: unless-stopped

  # Servicio opcional para migraciones
  migration:
    build: .
    container_name: sesame_migration
    environment:
      DATABASE_URL: ${DATABASE_URL}
    command: python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized successfully')"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - sesame_network
    profiles:
      - migration

networks:
  sesame_network:
    driver: bridge

volumes:
  postgres_data:
```

## Comandos de Despliegue

### Construcción e Inicio

```bash
# Construir las imágenes
docker-compose build

# Inicializar la base de datos (primera vez)
docker-compose --profile migration up migration

# Iniciar los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f web

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: elimina datos)
docker-compose down -v
```

### Migraciones de Base de Datos

Para ejecutar migraciones después del despliegue inicial:

```bash
# Acceder al contenedor
docker exec -it sesame_app bash

# Ejecutar migraciones manualmente
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Configuración Inicial

### 1. Acceder a la Aplicación

Una vez iniciados los contenedores, acceder a:
```
http://localhost:5000
```

### 2. Iniciar Sesión

Usar las credenciales configuradas en el archivo `.env`:
- Usuario: El valor de `ADMIN_USERNAME`
- Contraseña: El valor de `ADMIN_PASSWORD`

### 3. Configurar Token API de Sesame

1. Navegar a "Conexión" en el menú
2. Ingresar el token de API de Sesame
3. Seleccionar la región correspondiente (EU1, EU2, US1, etc.)
4. Hacer clic en "Probar Conexión" para verificar
5. Guardar la configuración

### 4. Obtener Token de API de Sesame

Para obtener un token de API de Sesame:
1. Acceder a tu cuenta de Sesame
2. Ir a Configuración → API
3. Generar un nuevo token
4. Copiar el token generado

## Estructura del Proyecto

```
sesame-report-generator/
├── app.py                  # Configuración principal de Flask
├── main.py                 # Punto de entrada de la aplicación
├── auth.py                 # Sistema de autenticación
├── models.py               # Modelos de base de datos
├── routes/                 # Rutas y endpoints
│   └── main.py            # Rutas principales
├── services/              # Lógica de negocio
│   ├── sesame_api.py      # Integración con API de Sesame
│   ├── no_breaks_report_generator.py  # Generador de reportes
│   └── check_types_service.py         # Gestión de tipos de actividad
├── templates/             # Plantillas HTML
├── static/                # Archivos estáticos
├── temp_reports/          # Almacenamiento temporal de reportes
└── logs/                  # Archivos de log

```

## Características de Seguridad

- 🔐 Autenticación requerida para todas las rutas
- 🔑 Tokens API encriptados en base de datos
- 🛡️ Protección CSRF habilitada
- 📝 Registro detallado de actividades
- 🔒 Variables sensibles en variables de entorno
- ⏰ Sesiones con tiempo de expiración

## Solución de Problemas

### La aplicación no se conecta a la base de datos

```bash
# Verificar que PostgreSQL esté ejecutándose
docker-compose ps

# Verificar logs de la base de datos
docker-compose logs db

# Reiniciar servicios
docker-compose restart
```

### Error de permisos en archivos

```bash
# Dar permisos a directorios
chmod -R 755 temp_reports logs
```

### Problemas con el token de API

1. Verificar que el token sea válido en Sesame
2. Confirmar la región correcta (EU1, EU2, US1, etc.)
3. Revisar logs para mensajes de error específicos

### Reportes que no se generan

```bash
# Ver logs del contenedor web
docker-compose logs -f web --tail=100

# Verificar espacio en disco
df -h

# Limpiar reportes antiguos
docker exec sesame_app rm -rf temp_reports/*
```

## Mantenimiento

### Limpieza de Reportes Antiguos

La aplicación mantiene automáticamente un máximo de 10 reportes. Para limpieza manual:

```bash
docker exec sesame_app python -c "
import os
import glob
files = glob.glob('temp_reports/*.xlsx')
for f in files:
    os.remove(f)
print(f'Eliminados {len(files)} reportes')
"
```

### Backup de Base de Datos

```bash
# Crear backup
docker exec sesame_postgres pg_dump -U sesame_user sesame_reports > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker exec -i sesame_postgres psql -U sesame_user sesame_reports < backup_20240814.sql
```

### Actualización de la Aplicación

```bash
# Detener servicios
docker-compose down

# Obtener últimos cambios
git pull origin main

# Reconstruir imagen
docker-compose build

# Iniciar servicios actualizados
docker-compose up -d
```

## Monitoreo

### Ver Estado de Servicios

```bash
# Estado de contenedores
docker-compose ps

# Uso de recursos
docker stats

# Logs en tiempo real
docker-compose logs -f
```

### Métricas de Rendimiento

La aplicación registra métricas en `/app/logs/`:
- `app.log`: Log general de la aplicación
- `error.log`: Errores y excepciones
- `access.log`: Accesos HTTP

## Variables de Entorno Disponibles

| Variable | Descripción | Requerida | Default |
|----------|-------------|-----------|---------|
| `ADMIN_USERNAME` | Usuario administrador | ✅ | - |
| `ADMIN_PASSWORD` | Contraseña administrador | ✅ | - |
| `DATABASE_URL` | URL de conexión PostgreSQL | ✅ | - |
| `FLASK_SECRET_KEY` | Clave secreta Flask | ✅ | - |
| `SESSION_SECRET` | Clave de sesión | ✅ | - |
| `PORT` | Puerto de la aplicación | ❌ | 5000 |
| `WEB_CONCURRENCY` | Número de workers Gunicorn | ❌ | 4 |
| `LOG_LEVEL` | Nivel de logging | ❌ | INFO |
| `MAX_REPORTS` | Máximo de reportes almacenados | ❌ | 10 |

## Soporte

Para reportar problemas o solicitar características:
1. Revisar los logs de la aplicación
2. Verificar la configuración de variables de entorno
3. Asegurar que los servicios estén ejecutándose correctamente

## Licencia

Proyecto privado - Todos los derechos reservados

---

**Nota**: Este sistema está diseñado para uso interno empresarial. Asegurar que todas las credenciales y tokens se mantengan seguros y no se compartan públicamente.