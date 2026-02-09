# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git

# Copy just the requirements file first
COPY requirements_full.txt requirements.txt

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the code
COPY . .

# Set the command to run your script
CMD ["python", "script.py", "run-auto"]