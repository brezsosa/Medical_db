import os
import pandas as pd
import mysql.connector
import time
import numpy as np

# --- Configuración de la Base de Datos ---
DB_HOST = "127.0.0.1"  # Usamos 127.0.0.1 (localhost) ya que Docker mapea el puerto
DB_PORT = 3306         # Puerto por defecto de MySQL
DB_USER = "root"
DB_PASSWORD = "pass_05" # Debe coincidir con MYSQL_ROOT_PASSWORD en docker-compose.yml
DB_NAME = "data_medical"      # Debe coincidir con MYSQL_DATABASE en docker-compose.yml

# --- Configuración de la Carpeta de CSVs ---
CSV_FOLDER = "../data" # Ruta a tu carpeta con los archivos .csv

# --- Definición de Claves Primarias y Foráneas ---
# Define claves primarias.
# Formato: { "nombre_tabla": "nombre_columna_pk" }
PRIMARY_KEYS = {
    "diagnosticos": "diagnostico_id",
    "medicacion": "medicacion_id",
    "pacientes": "paciente_id",
    "profesionales": "profesionales_id"
}

# Define claves foráneas
# Formato: [
#   {"from_table": "tabla_origen", "from_column": "columna_origen", "to_table": "tabla_destino", "to_column": "columna_destino"},
#   ...
# ]
FOREIGN_KEYS = [
    {"from_table": "metabolico", "from_column": "paciente_id", "to_table": "pacientes", "to_column": "paciente_id"},
    {"from_table": "tratamientos", "from_column": "medicacion_id", "to_table": "medicacion", "to_column": "medicacion_id"},
    {"from_table": "tratamientos", "from_column": "profesionales_id", "to_table": "profesionales", "to_column": "profesionales_id"},
    {"from_table": "tratamientos", "from_column": "diagnostico_id", "to_table": "diagnosticos", "to_column": "diagnostico_id"},
    {"from_table": "tratamientos", "from_column": "paciente_id", "to_table": "pacientes", "to_column": "paciente_id"}

]

# --- Funciones para manejar la base de datos ---
def get_db_connection():
    """Establece y devuelve una conexión a la base de datos MySQL"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print(f"Conexión a la base de datos MySQL establecida exitosamente.")
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos MySQL.")
        if "Unknown database" in str(err):
            print(f"La base de datos '{DB_NAME}' podría no existir aún. Asegúrate de que el contenedor Docker esté completamente inicializado.")
        return None

def create_table_from_dataframe(cursor, df, table_name):
    """Crea una tabla en MySQL a partir de la estructura de un DataFrame de Pandas."""
    columns_sql = []
    for col_name, dtype in df.dtypes.items():
        # Limpiar y asegurar el nombre de la columna para MySQL
        clean_col_name = "".join(c for c in col_name if c.isalnum() or c == "_").lower()
        if not clean_col_name:
            print(f"Advertencia: La columna '{col_name}' resultó en un nombre de columna vacío. Saltando.")
            continue

        # Mapeo de tipos de Pandas a MySQL (puedes expandir esto)
        if 'int' in str(dtype):
            sql_type = "BIGINT" # Usar BIGINT para enteros más grandes
        elif 'float' in str(dtype):
            sql_type = "DOUBLE" # Usar DOUBLE para mayor precisión
        elif 'bool' in str(dtype):
            sql_type = "BOOLEAN"
        elif 'datetime' in str(dtype):
            sql_type = "DATETIME"
        else:
            sql_type = "VARCHAR(255)" # Por defecto para strings, ajusta el tamaño si sabes que son más grandes
        
        columns_sql.append(f"`{clean_col_name}` {sql_type}")

    create_table_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(columns_sql)})"
    print(f"Generando SQL para tabla {table_name}: {create_table_query}")
    try:
        cursor.execute(create_table_query)
        print(f"Tabla '{table_name}' creada/verificada.")
        return True
    except mysql.connector.Error as err:
        print(f"Error al crear la tabla '{table_name}': {err}")
        return False

def insert_data_into_table(conn, cursor, df, table_name):
    """Inserta los datos de un DataFrame en la tabla especificada."""
    if df.empty:
        print(f"El DataFrame para la tabla '{table_name}' está vacío. No se insertarán datos.")
        return

    # Limpiar y asegurar los nombres de las columnas para la consulta INSERT
    clean_columns = [f"`{''.join(c for c in col if c.isalnum() or c == '_').lower()}`" for col in df.columns]
    columns_str = ", ".join(clean_columns)
    
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

    # Convertir DataFrame a una lista de tuplas para la inserción
    # Pandas DataFrame.values ya produce una lista de filas, pero lo convertimos a tuplas
    # Asegúrate de que los tipos de datos en el DataFrame coincidan con los de la tabla MySQL
    df_copy = df.copy()
    df_copy = df_copy.replace({pd.NA: None, pd.NaT: None})
    data_to_insert = [tuple(row) for row in df_copy.values]

    print(f"Insertando {len(data_to_insert)} filas en la tabla '{table_name}'...")
    data_to_insert = []
    for index, row in df.iterrows():
        # Convertir cada valor a un tipo de Python nativo.
        # Esto es crucial para manejar los tipos de NumPy.
        processed_row = []
        for item in row.values:
            if isinstance(item, (np.integer, np.int64, np.int32)):
                processed_row.append(int(item)) # Convertir enteros de NumPy a int de Python
            elif isinstance(item, (np.floating, np.float64, np.float32)):
                processed_row.append(float(item)) # Convertir flotantes de NumPy a float de Python
            elif pd.isna(item): # Manejar NaN (valores faltantes) de Pandas/NumPy
                processed_row.append(None) # Convertir NaN a None (que MySQL interpreta como NULL)
            else:
                processed_row.append(item) # Dejar otros tipos (strings, etc.) como están
        data_to_insert.append(tuple(processed_row))
        
    try:
        cursor.executemany(insert_query, data_to_insert)
        conn.commit() # Confirmar los cambios
        print(f"Datos insertados exitosamente en la tabla '{table_name}'.")
    except mysql.connector.Error as err:
        print(f"Error al insertar datos en la tabla '{table_name}': {err}")
        conn.rollback() # Revertir cambios en caso de error

def add_primary_keys(conn, cursor):
    """Agrega claves primarias a las tablas según la configuración."""
    print("\n--- Agregando Claves Primarias ---")
    for table, pk_column in PRIMARY_KEYS.items():
        # Limpiar el nombre de la columna para asegurar que sea válido en MySQL
        clean_pk_column = "".join(c for c in pk_column if c.isalnum() or c == "_").lower()
        
        alter_table_query = f"ALTER TABLE `{table}` ADD PRIMARY KEY (`{clean_pk_column}`)"
        try:
            # Verificar si la clave primaria ya existe para evitar errores
            cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY'")
            if cursor.fetchone():
                print(f"La tabla '{table}' ya tiene una clave primaria. Saltando.")
                continue

            print(f"Agregando PK a '{table}' en columna '{clean_pk_column}': {alter_table_query}")
            cursor.execute(alter_table_query)
            conn.commit()
            print(f"Clave primaria agregada a '{table}'.")
        except mysql.connector.Error as err:
            if err.errno == 1068: # Error 1068: Multiple primary key defined
                print(f"Advertencia: La tabla '{table}' ya tiene una clave primaria. No se modificó.")
            elif err.errno == 1075: # Error 1075: Incorrect table definition; there can be only one auto column and it must be defined as a key
                print(f"Advertencia: La columna '{clean_pk_column}' en '{table}' podría no ser única o es auto_increment sin ser clave. Error: {err}")
            else:
                print(f"Error al agregar clave primaria a '{table}': {err}")

def add_foreign_keys(conn, cursor):
    """Agrega claves foráneas a las tablas según la configuración."""
    print("\n--- Agregando Claves Foráneas ---")
    for fk_info in FOREIGN_KEYS:
        from_table = fk_info["from_table"]
        from_column = "".join(c for c in fk_info["from_column"] if c.isalnum() or c == "_").lower()
        to_table = fk_info["to_table"]
        to_column = "".join(c for c in fk_info["to_column"] if c.isalnum() or c == "_").lower()

        # Generar el nombre de la FK y truncarlo si es necesario
        base_fk_name = f"fk_{from_table}_{from_column}_to_{to_table}_{to_column}"
        
        # MySQL por defecto tiene un límite de 64 caracteres para identificadores.
        # Puedes ajustar este número si sabes que tu DB tiene un límite diferente.
        MAX_FK_NAME_LENGTH = 64 

        if len(base_fk_name) > MAX_FK_NAME_LENGTH:
            # Opción 1: Truncar y agregar un hash para asegurar unicidad
            import hashlib
            hash_suffix = hashlib.md5(base_fk_name.encode()).hexdigest()[:3] # Usar un hash corto del nombre original
            fk_name = f"fk_{from_table}_{from_column}_{hash_suffix}"
            # Asegurarse de que el nombre final no exceda el límite
            fk_name = fk_name[:MAX_FK_NAME_LENGTH] 
            print(f"Advertencia: El nombre de FK '{base_fk_name}' era demasiado largo. Se ha truncado a '{fk_name}'.")
        else:
            fk_name = base_fk_name

        alter_table_query = f"""
        ALTER TABLE `{from_table}`
        ADD CONSTRAINT `{fk_name}`
        FOREIGN KEY (`{from_column}`) REFERENCES `{to_table}`(`{to_column}`)
        ON DELETE RESTRICT ON UPDATE CASCADE;
        """
        # ON DELETE RESTRICT: Si intentas borrar una fila de la tabla padre que tiene filas hijas, la operación fallará.
        # ON UPDATE CASCADE: Si se actualiza el valor de la clave primaria en la tabla padre, se actualiza automáticamente
        #                     en la tabla hija.

        try:
            # Verificar si la clave foránea ya existe
            cursor.execute(f"SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = '{DB_NAME}' AND TABLE_NAME = '{from_table}' AND CONSTRAINT_NAME = '{fk_name}'")
            if cursor.fetchone():
                print(f"La clave foránea '{fk_name}' ya existe. Saltando.")
                continue

            print(f"Agregando FK: {from_table}.{from_column} -> {to_table}.{to_column}")
            cursor.execute(alter_table_query)
            conn.commit()
            print(f"Clave foránea '{fk_name}' agregada.")
        except mysql.connector.Error as err:
            if err.errno == 1005:
                print(f"Error (1005) al agregar FK '{fk_name}': {err}. Posiblemente tipos de datos no coinciden o valores no existen en la tabla referenciada.")
            elif err.errno == 1060: # Duplicate column name (este error usualmente no es para FKs)
                print(f"Advertencia: La clave foránea '{fk_name}' ya existe. No se añadió nuevamente.")
            elif err.errno == 1059: # Identifier name too long
                print(f"¡Error Crítico! El nombre de la clave foránea '{fk_name}' es demasiado largo ({len(fk_name)} caracteres) incluso después de intentar truncarlo. Considera un esquema de nombres más corto o ajusta el límite de caracteres si tu DB lo permite.")
            else:
                print(f"Error al agregar clave foránea '{fk_name}': {err}")

def main():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("No se pudo establecer conexión con la base de datos. Asegúrate de que el contenedor Docker esté funcionando.")
            return

        cursor = conn.cursor()

        # Asegurarse de que la carpeta de CSVs exista
        if not os.path.isdir(CSV_FOLDER):
            print(f"Error: La carpeta '{CSV_FOLDER}' no existe. Por favor, créala y coloca tus archivos CSV dentro.")
            return

        csv_files = [f for f in os.listdir(CSV_FOLDER) if f.endswith(".csv")]

        if not csv_files:
            print(f"No se encontraron archivos .csv en la carpeta '{CSV_FOLDER}'.")
            return

        for csv_file in csv_files:
            file_path = os.path.join(CSV_FOLDER, csv_file)
            
            # Nombre de la tabla será el nombre del archivo sin extensión
            table_name = os.path.splitext(csv_file)[0] 
            # Limpiar el nombre de la tabla para asegurar que sea válido en MySQL
            table_name = "".join(c for c in table_name if c.isalnum() or c == "_").lower()
            if not table_name:
                print(f"Advertencia: El nombre de archivo '{csv_file}' resultó en un nombre de tabla vacío o inválido. Saltando.")
                continue

            print(f"\n--- Procesando archivo: {csv_file} ---")
            try:
                # Leer el archivo CSV
                df = pd.read_csv(file_path, encoding='latin1', sep=';', low_memory=False)
                print(f"Archivo '{csv_file}' leído. {len(df)} filas encontradas.")
                
                # Crear la tabla
                if create_table_from_dataframe(cursor, df, table_name):
                    # Insertar los datos
                    insert_data_into_table(conn, cursor, df, table_name)

            except pd.errors.EmptyDataError:
                print(f"El archivo '{csv_file}' está vacío. Saltando.")
            except FileNotFoundError:
                print(f"Error: El archivo '{csv_file}' no se encontró. Verifica la ruta.")
            except Exception as e:
                print(f"Error inesperado al procesar el archivo '{csv_file}': {e}")

        # --- Agrega las claves primarias y foráneas después de cargar todos los datos ---
        add_primary_keys(conn, cursor)
        add_foreign_keys(conn, cursor)

    finally:
        if conn:
            conn.close()
            print("\n\nConexión a la base de datos cerrada.")

if __name__ == "__main__":
    main()