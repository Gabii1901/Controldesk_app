from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host= "45.163.12.10", port=5432, debug=False)
