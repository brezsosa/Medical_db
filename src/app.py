import time
import subprocess
import os

def ejecutar_comando(comando, mensaje):
    """Función auxiliar para ejecutar comandos de shell y proporcionar retroalimentación."""
    print(f"--- {mensaje} ---")
    try:
        # subprocess.run ejecuta el comando.
        # check=True: Si el comando falla, levanta una excepción CalledProcessError.
        # shell=True: Permite pasar el comando como una cadena de texto.
        # text=True: Decodifica stdout y stderr como texto.
        # capture_output=True: Captura la salida y los errores del comando.
        proceso = subprocess.run(comando, check=True, shell=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR: {mensaje} FALLÓ ---")
        print(f"Comando: {e.cmd}")
        print(f"Código de Retorno: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        exit(1) # Salir del script si algún comando falla

def main():
    # Obtener el directorio donde se encuentra app.py
    directorio_script = os.path.dirname(os.path.abspath(__file__))
    
    # Cambiar al directorio 'src' (donde están app.py, crea_csv.py, crea_db.py)
    os.chdir(directorio_script)

    # 1. Crear los archivos CSV necesarios
    ejecutar_comando("python crea_csv.py", "Creando archivos CSV")
    time.sleep(5)  # Esperar a que los archivos se creen correctamente

    # 2. Crear la imagen del servidor MYSQL en un contenedor Docker
    directorio_padre = os.path.join(directorio_script, os.pardir)
    os.chdir(directorio_padre) 
    ejecutar_comando("docker-compose up -d", "Iniciando contenedor Docker")
    time.sleep(30) # Esperar a que el contenedor se inicie correctamente

    # Volver al directorio 'src'
    os.chdir(directorio_script)

    # 3. Crear la base de datos de la aplicación
    ejecutar_comando("python crea_db.py", "Creando la base de datos de la aplicación")

    print("\n--- ¡Todas las operaciones se completaron exitosamente! ---")

if __name__ == "__main__":
    main()