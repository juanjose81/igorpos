import sys
import os

# Asegurar que Vercel encuentre la carpeta app
sys.path.append(os.path.dirname(__file__))

from app import create_app

app = create_app()