# # Use an official Python runtime as a parent image
# FROM python:3.8-slim

# # Set environment variables for Python to run in unbuffered mode and Django to not prompt for input
# ENV PYTHONUNBUFFERED 1
# ENV DJANGO_SETTINGS_MODULE web_project.settings

# # Create and set the working directory in the container
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#        postgresql-client \
#        && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Install Python dependencies
# COPY requirements.txt /app/
# RUN pip install --upgrade pip \
#     && pip install -r requirements.txt

# # Install Gunicorn
# RUN pip install gunicorn

# # Copy the local Django project directory into the container
# COPY . /app/

# # Collect static files and perform database migrations (customize these according to your project)
# RUN python manage.py collectstatic --noinput
# RUN python manage.py migrate

# # Expose the port the application runs on
# EXPOSE 8000

# # Start the application using Gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "web_project.wsgi:application"]
# Use an official Python runtime as a parent image


# FROM python:3.8-slim

# # Set environment variables for Python to run in unbuffered mode and Django to not prompt for input
# ENV PYTHONUNBUFFERED 1
# ENV DJANGO_SETTINGS_MODULE web_project.settings

# # Create and set the working directory in the container
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#        default-libmysqlclient-dev \
#        && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Install Python dependencies
# COPY requirements.txt /app/
# RUN pip install --upgrade pip \
#     && pip install -r requirements.txt

# RUN pip install gunicorn

# # Copy the local Django project directory into the container
# COPY . /app/

# # Collect static files and perform database migrations (customize these according to your project)
# RUN python manage.py collectstatic --noinput
# RUN python manage.py migrate
# # Expose the port the application runs on

# RUN python manage.py makemigrations
# RUN python manage.py migrate
# RUN python manage.py create_users
# EXPOSE 8000

# # Start the application
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "web_project.wsgi:application"]


# Use an official Python runtime as a parent image
FROM python:3.8-slim

# RUN pip install mysqlclient --prefer-binary

# Install required system packages including pkg-config
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pkg-config \
       default-libmysqlclient-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#RUN pip install mysqlclient
# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

RUN python manage.py collectstatic --noinput
# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000
# Run app.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:8000", "web_project.wsgi:application"]

