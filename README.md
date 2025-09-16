# Catanduanes Connect

A web platform connecting job seekers and businesses in Catanduanes, Philippines.

## Features

- Job posting and searching
- Business directory
- Location-based search
- User authentication
- Business profiles
- Job applications
- Reviews and ratings
- Messaging system

## Tech Stack

- Python 3.8+
- Flask
- SQLAlchemy
- Bootstrap 5
- JavaScript
- HTML5/CSS3

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/catanduanes-connect.git
cd catanduanes-connect
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///catanduanes_connect.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Project Structure

```
catanduanes-connect/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── static/            # Static files
│   ├── css/          # CSS files
│   ├── js/           # JavaScript files
│   └── images/       # Image assets
├── templates/         # HTML templates
│   ├── auth/         # Authentication templates
│   ├── dashboard/    # Dashboard templates
│   └── ...
└── .env              # Environment variables
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any inquiries, please contact:
- Email: contact@catanduanesconnect.com
- Website: https://catanduanesconnect.com 