# Use the official Microsoft Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory inside the container
WORKDIR /app

# Copy dependency list and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot files into the container
COPY . .

# Command to run your bot script
CMD ["python", "multi.py"]
