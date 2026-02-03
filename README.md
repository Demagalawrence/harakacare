# HarakaCare

A Django-based web application for healthcare management.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd harakacare
```

### 2. Create and Activate Virtual Environment (Recommended)

#### On Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root and add the following variables:

```
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser to view the application.

## Project Structure

- `apps/`: Contains all Django applications
- `harakacare/`: Main project configuration
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript, images)
- `media/`: User-uploaded files
- `tests/`: Test files

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

This project follows PEP 8 style guidelines. Before committing, please ensure your code is properly formatted.

## Deployment

For production deployment, make sure to:
1. Set `DEBUG=False` in your environment variables
2. Configure a proper database (PostgreSQL recommended)
3. Set up a proper web server (Nginx + Gunicorn recommended)
4. Configure proper static files handling

## License

[Specify your license here]
