from flask import Flask, redirect, url_for, session
from config import Config
from database import init_db

# ── Blueprints ────────────────────────────────────────────────
from auth.routes          import auth_bp
from routes.dashboard_routes   import dashboard_bp
from routes.log_routes         import log_bp
from routes.recommend_routes   import recommend_bp
from routes.performance_routes import performance_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Initialize database ───────────────────────────────────
    with app.app_context():
        init_db()

    # ── Register blueprints ───────────────────────────────────
    app.register_blueprint(auth_bp,        url_prefix="/auth")
    app.register_blueprint(dashboard_bp,   url_prefix="/dashboard")
    app.register_blueprint(log_bp,         url_prefix="/log")
    app.register_blueprint(recommend_bp,   url_prefix="/recommend")
    app.register_blueprint(performance_bp, url_prefix="/performance")

    # ── Root redirect ─────────────────────────────────────────
    @app.route("/")
    def index():
        if "student_id" in session:
            return redirect(url_for("dashboard.home"))
        return redirect(url_for("auth.login"))

    # ── 404 handler ───────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Page not found"}, 404

    # ── 500 handler ───────────────────────────────────────────
    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app


# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)