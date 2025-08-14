-- Archivo de inicialización de base de datos
-- Este archivo se ejecuta automáticamente cuando se crea el contenedor de PostgreSQL

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configurar zona horaria
SET TIME ZONE 'UTC';

-- Crear índices para mejorar rendimiento (se ejecutarán después de crear las tablas)
-- Los índices reales se crearán automáticamente por SQLAlchemy