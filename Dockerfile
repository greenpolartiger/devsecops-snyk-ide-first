FROM python:3.13-slim

# VULN: Running as root user
# Should use: RUN useradd -m appuser && USER appuser
WORKDIR /app

# VULN: Copying secrets in build context
COPY . .

# VULN: No health check
# Should have: HEALTHCHECK CMD curl -f http://localhost:5000/ || exit 1

# VULN: Exposing port without documentation
EXPOSE 5000

# VULN: No layer caching optimization
RUN pip install --no-cache-dir -r requirements.txt

# VULN: Hardcoded environment variables exposed
ENV FLASK_ENV=production \
    API_KEY=sk-1234567890abcdefghijklmnop \
    DB_PASSWORD=admin123

CMD ["python", "app.py"]