# Use a lightweight Python image
FROM python:3.9-slim

# Set a build argument for version
ARG VERSION
# Pass the build argument as an environment variable
ENV B_NUM=$VERSION

# Set the working directory
WORKDIR /app

# Copy only the requirements first for efficient caching
COPY ./requirements.txt /app/requirements.txt

# Install necessary dependencies
RUN pip install --no-cache-dir schedule
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application files
COPY . /app

# Expose the port the app will run on
EXPOSE 5000

# Command to run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
