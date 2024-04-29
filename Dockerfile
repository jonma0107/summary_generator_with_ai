# Usa una imagen oficial de Python con Alpine para menor tamaño
FROM python:3.11-alpine

# Establece la variable de entorno para evitar buffering
ENV PYTHONUNBUFFERED=1

# Crea y usa un directorio de trabajo dentro del contenedor
WORKDIR /backend

# Copia el archivo de dependencias antes de copiar el código (mejora el cache de Docker)
COPY ./requirements.txt /requirements.txt

# Instala dependencias necesarias para PostgreSQL, Gunicorn y ffmpeg para transcribir audio
RUN apk add --update --no-cache \
        postgresql-client \
        build-base \
        postgresql-dev \
        gcc \
        ffmpeg \ 
        musl-dev \
        libffi-dev && \
    python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /requirements.txt && \
    apk del build-base postgresql-dev

# Establece el PATH para usar el entorno virtual
ENV PATH="/py/bin:$PATH"

# Copia el código del backend al contenedor
COPY . /backend

# Exponer el puerto por defecto de Django
EXPOSE 8000

# Comando para ejecutar migraciones, recolectar archivos estáticos y luego iniciar el servidor
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py makemigrations --noinput && python manage.py migrate && gunicorn ai_blog.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --worker-class gevent --log-level debug"]
