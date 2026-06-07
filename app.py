from app import create_app

app = create_app()

if __name__ == '__main__':
    # Runs the Flask application on port 8000 with environment configuration settings
    # To run: python app.py
    from urllib.parse import urlparse
    base_url = app.config.get('BASE_URL', 'http://127.0.0.1:8000')
    parsed_url = urlparse(base_url)
    
    host = parsed_url.hostname or '127.0.0.1'
    port = parsed_url.port or 8000

    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG']
    )

