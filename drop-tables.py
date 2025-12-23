from src.config import DatabaseConfig
from src.database import GrailDatabase
import psycopg2
config = DatabaseConfig()
params = config.get_connection_params()
conn = psycopg2.connect(**params)
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS grail_files CASCADE')
conn.commit()
cursor.close()
conn.close()
print('Table dropped successfully!')