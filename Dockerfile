# Use a lightweight official Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Command to run your bot script
CMD ["python", "bot.py"]
