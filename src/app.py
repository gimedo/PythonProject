from flask import Flask, request, jsonify, render_template
import pymysql
from psycopg2 import connect as psycopg2_connect, OperationalError
from threading import Thread, Lock
import time
from config import DevelopmentConfig

app = Flask(__name__)

# Cargar la configuración de desarrollo
app.config.from_object(DevelopmentConfig)

# Lista de registros procesados
registro_resultado = []

# Estado de la API
api_active = True

# Bloqueo para asegurar que solo un hilo puede modificar api_active a la vez
api_lock = Lock()

# Conexión a MySQL
def get_mysql_connection():
    try:
        return pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB']
        )
    except pymysql.MySQLError as e:
        print(f"Error al conectar con MySQL: {e}")
        return None

# Conexión a PostgreSQL
def get_postgresql_connection():
    try:
        return psycopg2_connect(
            dbname=app.config['POSTGRESQL_DB'],
            user=app.config['POSTGRESQL_USER'],
            password=app.config['POSTGRESQL_PASSWORD'],
            host=app.config['POSTGRESQL_HOST'],
            port=app.config['POSTGRESQL_PORT']
        )
    except OperationalError as e:
        print(f"Error al conectar con PostgreSQL: {e}")
        return None

# Proceso de sincronización
def sync_data():
    global registro_resultado
    while True:
        with api_lock:
            if not api_active:
                print("API desactivada. Esperando para reactivar.")
                time.sleep(60)  # Si la API está desactivada, espera antes de comprobar nuevamente
                continue

        mysql_conn = None
        postgres_conn = None
        try:
            # Obtener conexiones
            mysql_conn = get_mysql_connection()
            postgres_conn = get_postgresql_connection()

            if not mysql_conn or not postgres_conn:
                print("No se pudo establecer la conexión a las bases de datos.")
                return

            with mysql_conn.cursor() as mysql_cursor, postgres_conn.cursor() as postgres_cursor:
                # Consulta los datos nuevos desde MySQL
                print("Consultando datos desde MySQL...")
                mysql_cursor.execute("""SELECT nrocentral, nroticket, fecha, idempresa, ruc, razonSocial, EESS, terminal_cac,
                                           nrotarjeta, identif_disp, total_sin_impuestos, ventas, total_con_impuestos, 
                                           docchofer, cantidad, codproducto, producto, PRECIOS
                                    FROM VENTAS_ALIANZA
                                    WHERE fecha > (NOW() - INTERVAL 1 DAY)""")
                rows = mysql_cursor.fetchall()

                if not rows:
                    print("No se encontraron registros nuevos en MySQL.")
                else:
                    print(f"Se encontraron {len(rows)} registros para sincronizar.")

                # Insertar los datos en PostgreSQL
                for row in rows:
                    try:
                        print(f"Ingresando registro nrocentral: {row[0]} en PostgreSQL")
                        postgres_cursor.execute(""" 
                            INSERT INTO ventas_eess (
                                nrocentral, nroticket, fecha, idempresa, ruc, razonSocial, EESS, terminal_cac,
                                nrotarjeta, identif_disp, total_sin_impuestos, ventas, total_con_impuestos, 
                                docchofer, cantidad, codproducto, producto, PRECIOS
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                        """, row)
                        postgres_conn.commit()

                        # Añadir el registro procesado a la lista de resultados
                        registro_resultado.append({
                            'nrocentral': row[0], 'status': 'success'
                        })
                    except Exception as e:
                        print(f"Error al insertar registro nrocentral {row[0]} en PostgreSQL: {e}")
                        registro_resultado.append({
                            'nrocentral': row[0], 'status': 'error', 'error': str(e)
                        })

        except Exception as e:
            print(f"Error en la sincronización: {e}")
        finally:
            if mysql_conn:
                mysql_conn.close()
            if postgres_conn:
                postgres_conn.close()

        time.sleep(60)  # Ejecutar cada minuto

# Ruta para activar/desactivar la API
@app.route('/toggle-api', methods=['POST'])
def toggle_api():
    global api_active
    with api_lock:
        api_active = not api_active
    return jsonify({"api_active": api_active})

# Ruta para ver el estado de la API
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"api_active": api_active})

# Ruta para mostrar los registros procesados
@app.route('/registros', methods=['GET'])
def ver_registros():
    return jsonify({"registros": registro_resultado})

# Ruta para la interfaz web
@app.route('/')
def index():
    return render_template('index.html', registros=registro_resultado, api_active=api_active)

# Iniciar sincronización en un hilo separado
Thread(target=sync_data, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)



