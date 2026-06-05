from app import create_app

app = create_app()

if __name__ == '__main__':
    # Runs the Flask application on port 5000 with environment configuration settings
    # To run: python app.py
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=app.config['DEBUG']
    )
