import os

base_dir = r"C:\Users\Marcelo-HP\Desktop\Codigo\Proyectos\cloud-native\ms-condominios"
env_py_path = os.path.join(base_dir, "alembic", "env.py")

with open(env_py_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace target_metadata = None with the actual one
content = content.replace("target_metadata = None", """
from app.config.settings import settings
from app.config.database import Base
import app.model.condominio
import app.model.outbox

config.set_main_option("sqlalchemy.url", settings.url_base_datos.replace("oracle+oracledb://", "oracle+oracledb_async://"))
target_metadata = Base.metadata
""")

with open(env_py_path, "w", encoding="utf-8") as f:
    f.write(content)

print("alembic/env.py updated")
