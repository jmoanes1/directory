# Production Deployment Guide

## Overview

This guide covers deploying the Employee Directory application to a production environment using Gunicorn, Nginx, PostgreSQL, and WhiteNoise for static files.

## Prerequisites

- Ubuntu 22.04+ / Debian 12+ server (or similar Linux)
- Python 3.12+
- PostgreSQL 14+
- Nginx
- Domain name with SSL certificate

## 1. Server Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx -y
```

## 2. PostgreSQL Configuration

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE employee_directory;
CREATE USER ed_user WITH PASSWORD 'strong_password_here';
ALTER ROLE ed_user SET client_encoding TO 'utf8';
ALTER ROLE ed_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ed_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE employee_directory TO ed_user;
\q
```

## 3. Application Setup

```bash
# Create application user
sudo adduser --disabled-password --gecos "" edapp
sudo su - edapp

# Clone project
git clone <your-repo-url> employee-directory
cd employee-directory

# Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Environment Configuration

Create `.env` in the project root:

```env
SECRET_KEY=generate-a-50-char-random-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=employee_directory
DB_USER=ed_user
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=email_password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Database Migration

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data   # Optional: initial data
python manage.py createsuperuser  # Or create admin manually
```

## 6. Gunicorn Systemd Service

Exit back to root/sudo user:

```bash
sudo nano /etc/systemd/system/employee-directory.service
```

```ini
[Unit]
Description=Employee Directory Gunicorn
After=network.target

[Service]
User=edapp
Group=www-data
WorkingDirectory=/home/edapp/employee-directory
Environment="PATH=/home/edapp/employee-directory/venv/bin"
ExecStart=/home/edapp/employee-directory/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/edapp/employee-directory/employee-directory.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl start employee-directory
sudo systemctl enable employee-directory
sudo systemctl status employee-directory
```

## 7. Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/employee-directory
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 10M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/edapp/employee-directory/staticfiles/;
    }

    location /media/ {
        alias /home/edapp/employee-directory/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/edapp/employee-directory/employee-directory.sock;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/employee-directory /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 8. SSL with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot auto-renews. Verify with:

```bash
sudo certbot renew --dry-run
```

## 9. Security Checklist

- [ ] `DEBUG=False` in production `.env`
- [ ] Strong `SECRET_KEY` (never commit to version control)
- [ ] Restricted `ALLOWED_HOSTS`
- [ ] HTTPS enabled with HSTS
- [ ] Database credentials secured
- [ ] Default seed passwords changed
- [ ] Firewall configured (UFW: allow 80, 443, SSH only)
- [ ] Regular PostgreSQL backups scheduled
- [ ] Media upload directory permissions restricted
- [ ] Log rotation configured

## 10. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 11. Backup Strategy

### Database Backup (daily cron)

```bash
# /home/edapp/backup.sh
#!/bin/bash
BACKUP_DIR=/home/edapp/backups
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -U ed_user employee_directory | gzip > $BACKUP_DIR/db_$DATE.sql.gz
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

```bash
chmod +x /home/edapp/backup.sh
crontab -e
# Add: 0 2 * * * /home/edapp/backup.sh
```

### Media Backup

```bash
rsync -av /home/edapp/employee-directory/media/ /backup/location/media/
```

## 12. Monitoring & Logs

```bash
# Application logs
sudo journalctl -u employee-directory -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 13. Updates & Maintenance

```bash
sudo su - edapp
cd employee-directory
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
exit
sudo systemctl restart employee-directory
```

## Docker Alternative (Optional)

For containerized deployment, create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: employee_directory
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    depends_on:
      - db
    env_file:
      - .env

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check Gunicorn service: `sudo systemctl status employee-directory` |
| Static files missing | Run `python manage.py collectstatic --noinput` |
| Database connection error | Verify `.env` credentials and PostgreSQL service |
| CSRF errors | Ensure `CSRF_TRUSTED_ORIGINS` includes your domain |
| Upload failures | Check `client_max_body_size` in Nginx and media directory permissions |

Add to `.env` for HTTPS deployments:

```env
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Add to `config/settings.py` if needed:

```python
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
```
