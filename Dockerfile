# Use the updated Microsoft Playwright Python image matching 1.62.0
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

# Set working directory inside the container
WORKDIR /app

# Copy dependency list and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot files into the container
COPY . .

# Command to run your bot script (use bot.py based on your repo)
CMD ["python", "bot.py"]
