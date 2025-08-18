from app import create_app

app = create_app()

if __name__ == "__main__":
    # Apenas para desenvolvimento local
    app.run(debug=True)
