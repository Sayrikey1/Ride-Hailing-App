# Ride Hailing App 🚗

Welcome to the Ride Hailing App! This project is a backend service for a ride-hailing application built with Django and Django REST Framework.

## Features ✨

- User Authentication and Authorization 🔐
- Role and Permission Management 🛡️
- Ride Booking and Management 🚕
- Payment Integration 💳
- Real-time Notifications 📲
- API Documentation 📄

## Project Structure 📁

```
.
├── .env
├── .gitignore
├── .vscode/
│   └── settings.json
├── accounts/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── constants/
│   ├── controllers/
│   ├── management/
│   ├── migrations/
│   ├── models.py
│   ├── serializers/
│   │   └── roles_permissions.py
│   ├── services/
│   ├── tasks.py
│   ├── tests.py
│   └── views.py
├── api/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── base_urls.py
│   ├── migrations/
│   ├── models.py
│   ├── tests.py
│   ├── urls/
│   └── views.py
├── business/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── controllers/
│   └── ...
├── core/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── crm/
├── db.sqlite3
├── manage.py
├── requirements.txt
├── ride-app/
│   ├── services/
│   ├── tests/
│   ├── trash.py
│   └── trash.txt
```

## Getting Started 🚀

### Prerequisites

- Python 3.8+
- Django 5.1.6
- Django REST Framework
- PostgreSQL

### Installation

1. Clone the repository:

```sh
git clone https://github.com/Sayrikey1/ride-hailing-app.git
cd ride-hailing-app
```

2. Create a virtual environment and activate it:

```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the dependencies:

```sh
pip install -r requirements.txt
```

4. Set up the environment variables:

Create a .env file in the root directory and add the necessary environment variables. Refer to `.env.example` for the required variables.

5. Apply the migrations:

```sh
python manage.py migrate
```

6. Run the development server:

```sh
python manage.py runserver
```

## Running Tests 🧪

To run the tests, use the following command:

```sh
python manage.py test
```

## API Documentation 📄

API documentation is available at `/api/docs/` when the server is running.

## Contributing 🤝

Contributions are welcome! Please open an issue or submit a pull request.

## License 📜

This project is licensed under the MIT License.

## Creator 👨‍💻

Created by [Sayrikey1](https://github.com/Sayrikey1). Feel free to reach out!

---

Enjoy coding! 🚀