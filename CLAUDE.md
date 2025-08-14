# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application that generates Excel and CSV reports from the Sesame Time Tracking API. The application provides a Spanish-language interface for businesses to create detailed employee activity reports with filtering capabilities for billing and time management purposes.

## Development Commands

### Running the Application
- **Development**: `python3 main.py` (runs on localhost:5001 with debug=True)
- **Production**: `gunicorn app:app` (configured for Replit deployment)
- **Note**: El puerto por defecto se cambió a 5001 para evitar conflictos con AirPlay en macOS

### Performance Testing
- **Test Optimizations**: `python3 test_optimizations.py` (verifica las optimizaciones de rendimiento)
- **Benchmark Reports**: Las optimizaciones reducen el tiempo de generación de >30min a <5min

### Dependencies
- Install dependencies: `pip install -r requirements.txt` or use `uv` if available
- Dependencies are defined in `pyproject.toml`

### Database Operations
- The app uses SQLAlchemy with PostgreSQL (configured via `DATABASE_URL` environment variable)
- Models are auto-created on app startup via `db.create_all()` in `app.py:34`
- No separate migration commands needed - schema changes are handled automatically

## Architecture Overview

### Core Structure
- **Entry Point**: `main.py` imports and runs the Flask app from `app.py`
- **Application Factory**: `app.py` contains the main Flask app configuration, database setup, and blueprint registration
- **Database Models**: `models.py` defines `SesameToken` and `CheckType` models using SQLAlchemy
- **Routes**: All routes are in `routes/main.py` using Flask Blueprint pattern
- **Services Layer**: API integration and business logic in `services/` directory

### Key Components
- **SesameAPI Service** (`services/sesame_api.py`): Handles all Sesame API communication with connection pooling, retry logic, and SSL handling
- **Report Generation** (`services/no_breaks_report_generator.py`): Creates Excel/CSV reports with threading for background processing
- **Check Types Service** (`services/check_types_service.py`): Manages activity type caching and synchronization
- **Parallel API** (`services/parallel_sesame_api.py`): Optimized API calls for large datasets

### Database Schema
- **sesame_tokens**: Stores API tokens with region configuration and active status
- **check_types**: Caches Sesame API activity types for performance and offline access

### Frontend Architecture
- **Templates**: Located in `templates/` using Jinja2 with `base.html` inheritance pattern
- **Styling**: Tailwind CSS via CDN with Figtree font and Tabler Icons
- **Static Files**: `static/style.css` for custom styles
- **Theme**: Dark theme with Indigo-500 primary color, Spanish language interface

### Report Management
- **Storage**: Generated reports stored in `temp_reports/` directory
- **Cleanup**: Automatic cleanup maintains maximum 10 reports
- **Formats**: Both Excel (.xlsx) and CSV export with UTF-8 BOM encoding
- **Background Processing**: Uses threading to prevent UI blocking during report generation
- **Performance**: OPTIMIZED with parallel API calls, caching, and batch processing for <5min generation times

## Important Configuration

### Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string o SQLite para desarrollo local (`sqlite:///instance/sesame_reports.db`)
- `SESSION_SECRET`: Flask session secret key
- `ADMIN_USERNAME`: Usuario para el sistema de autenticación
- `ADMIN_PASSWORD`: Contraseña para el sistema de autenticación

### Base de Datos Local
Para desarrollo local con SQLite:
```bash
mkdir -p instance
export DATABASE_URL="sqlite:///instance/sesame_reports.db"
export SESSION_SECRET="dev_secret_key_123"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin123"
python3 main.py
```

### API Integration
- **Base URL Pattern**: `https://api-{region}.sesametime.com` where region is configurable (eu1, eu2, etc.)
- **Token Management**: Stored in database with web interface for configuration
- **Token Validation**: La aplicación redirige automáticamente a `/conexion` si no hay token configurado
- **API Limits**: 500 records per page for time entries to optimize performance
- **Retry Logic**: Implemented with exponential backoff for SSL connection issues

## Development Guidelines

### Authentication Flow
- **Login**: Requiere `ADMIN_USERNAME` y `ADMIN_PASSWORD` configurados en variables de entorno
- **Token Validation**: Las rutas principales (`/` y `/descargas`) verifican automáticamente la existencia de un token activo
- **Auto-redirect**: Si no hay token configurado, redirige a `/conexion` con mensaje informativo
- **Session Management**: Utiliza Flask sessions para mantener el estado de autenticación

### Language Requirements
- **All communication, comments, and error messages must be in Spanish**
- Follow the patterns established in `.cursorrules` for consistent Spanish usage
- UI text and interface elements are in Spanish

### Code Patterns
- **Database Operations**: Use SQLAlchemy ORM, follow patterns in `models.py`
- **API Requests**: Use the SesameAPI class pattern with session reuse and retry logic
- **Error Handling**: Implement specific exception handling with Spanish error messages
- **Logging**: Use Python logging module, configured in `app.py` with INFO level
- **Threading**: Use for long-running operations (report generation) with proper state management

### Security Considerations
- API tokens are masked in UI display (`****` pattern)
- No tokens or credentials should appear in logs
- All routes are protected by authentication system
- Use HTTPS for external API communications

## Testing and Debugging
- Connection testing available via `/test-connection` endpoint
- Comprehensive logging configured to suppress urllib3 debug noise
- SSL connection issues are handled with timeout and retry mechanisms
- Progress tracking implemented for long-running report generation