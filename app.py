from flask import Flask, render_template
from routes.check import check_bp

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# register API blueprint
app.register_blueprint(check_bp)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)