from app import create_app, db

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    # Run the application
    with app.app_context():
        # Ensure database tables are created
        db.create_all()
    
    # Run the Flask development server
    app.run(debug=True, host='127.0.0.1', port=5000) 