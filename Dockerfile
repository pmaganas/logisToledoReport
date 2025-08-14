FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requerimientos primero (para aprovechar cache de Docker)
COPY pyproject.toml ./

# Instalar dependencias de Python
RUN pip install --no-cache-dir \
    Flask==3.0.3 \
    flask-sqlalchemy==3.1.1 \
    flask-login==0.6.3 \
    psycopg2-binary==2.9.9 \
    SQLAlchemy==2.0.31 \
    gunicorn==23.0.0 \
    requests==2.32.3 \
    openpyxl==3.1.5 \
    python-dateutil==2.9.0 \
    email-validator==2.2.0 \
    cryptography==43.0.0 \
    Werkzeug==3.0.3

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p temp_reports logs scripts

# Establecer permisos
RUN chmod -R 755 temp_reports logs && \
    chmod +x scripts/entrypoint.sh 2>/dev/null || true

# Exponer el puerto
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Usar el script de entrypoint si existe, sino usar comando directo
CMD ["/bin/bash", "-c", "if [ -f scripts/entrypoint.sh ]; then scripts/entrypoint.sh; else gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --reload --access-logfile logs/access.log --error-logfile logs/error.log main:app; fi"]