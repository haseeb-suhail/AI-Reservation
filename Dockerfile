# Use the official Python image as the base image
FROM python:3.10
# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg
# Set environment variables to prevent Python from writing .pyc files
# and to ensure that stdout and stderr streams are sent straight to the terminal
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Expose the port on which the Django server will run
EXPOSE 8000

# Entry point is now handled by docker-compose.yml, so no CMD here