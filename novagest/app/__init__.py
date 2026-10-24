from flask import Flask, render_template, redirect, url_for
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.clientes import clientes_bp
from app.routes.pos import pos_bp
from app.routes.reportes import reportes_bp
from app.routes.restaurante import restaurante_bp
from app.routes.caja_mesas import caja_mesas_bp
from app.routes.wompi_pagos import wompi_bp  # <-- Nuevo: Importamos tu módulo de pagos de Wompi

def create_app():
    app = Flask(__name__)
    app.secret_key = 'Novagest2026'

    # Registrar todos los blueprints (respetando estrictamente el orden que ya tenías)
    app.register_blueprint(caja_mesas_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(restaurante_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(wompi_bp)  # <-- Nuevo: Registramos el blueprint de Wompi

    # Ruta raíz para mostrar la Landing Page principal (index.html)
    @app.route('/')
    def index():
        return render_template('index.html')

    return app