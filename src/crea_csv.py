import os
import pandas as pd
import numpy as np
from faker import Faker
import random

# --- Configuración del Seed (Semilla) para reproducibilidad ---
# Puedes cambiar este número, pero si lo mantienes igual, los CSVs siempre serán los mismos.
RANDOM_SEED = 42 
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

# Configuración de Faker para nombres en español
fake = Faker('es_ES')

# --- Generación de Profesionales.csv ---
def generate_profesionales_csv(num_profesionales=17):
    profesionales = []
    for i in range(num_profesionales):
        profesionales.append({
            "profesionales_id": i + 1,
            "name": fake.name()
        })
    df_profesionales = pd.DataFrame(profesionales)
    df_profesionales.to_csv("../data/Profesionales.csv", index=False, sep=';')
    print(f"Profesionales.csv generado con {num_profesionales} registros.")
    return df_profesionales

# --- Generación de Diagnosticos.csv ---
def generate_diagnosticos_csv():
    diagnosticos_names = [
        "Esquizofrenia", "Trastorno Bipolar", "TAG", "TLP", "Depresion"
    ]
    diagnosticos = []
    for i, name in enumerate(diagnosticos_names):
        diagnosticos.append({
            "diagnostico_id": i + 1,
            "name": name
        })
    df_diagnosticos = pd.DataFrame(diagnosticos)
    df_diagnosticos.to_csv("../data/Diagnosticos.csv", index=False, sep=';')
    print(f"Diagnosticos.csv generado con {len(diagnosticos_names)} registros.")
    return df_diagnosticos

# --- Generación de Medicacion.csv ---
def generate_medicacion_csv():
    medicaciones = []
    
    # Antipsicóticos (6) - Nombres comunes
    antipsicoticos = [
        "Quetiapina", "Olanzapina", "Risperidona", 
        "Aripiprazol", "Haloperidol", "Clorpromazina"
    ]
    # Estabilizadores del ánimo (4)
    estabilizadores = [
        "Litio", "Ácido Valproico", "Lamotrigina", "Carbamazepina"
    ]
    # Antidepresivos (6)
    antidepresivos = [
        "Paroxetina", "Sertralina", "Fluoxetina", 
        "Venlafaxina", "Escitalopram", "Bupropion"
    ]
    # Benzodiacepinas (3)
    benzodiacepinas = [
        "Alprazolam", "Clonazepam", "Diazepam"
    ]
    
    all_medicaciones = antipsicoticos + estabilizadores + antidepresivos + benzodiacepinas
    
    for i, droga in enumerate(all_medicaciones):
        medicaciones.append({
            "medicacion_id": i + 1,
            "Droga": droga,
            "Tipo": (
                "Antipsicotico" if droga in antipsicoticos else
                "Estabilizador" if droga in estabilizadores else
                "Antidepresivo" if droga in antidepresivos else
                "Benzodiacepina"
            )
        })
    
    df_medicacion = pd.DataFrame(medicaciones)
    df_medicacion.to_csv("../data/Medicacion.csv", index=False, sep=';')
    print(f"Medicacion.csv generado con {len(all_medicaciones)} registros.")
    return df_medicacion, antipsicoticos # Devolvemos también la lista de antipsicóticos

# --- Generación de Pacientes.csv (nueva tabla) ---
def generate_pacientes_csv(num_pacientes=854):
    pacientes = []
    for i in range(1, num_pacientes + 1):
        pacientes.append({
            "paciente_id": i,
            "name": fake.name()
        })
    df_pacientes = pd.DataFrame(pacientes)
    df_pacientes.to_csv("../data/Pacientes.csv", index=False, sep=';')
    print(f"Pacientes.csv generado con {num_pacientes} registros.")
    return df_pacientes

# --- Generación de Tratamientos.csv (antes Pacientes.csv) ---
def generate_tratamientos_csv(df_profesionales, df_medicacion, df_diagnosticos, antipsicoticos_list, num_pacientes=854):
    tratamientos_data = []
    
    profesionales_ids = df_profesionales['profesionales_id'].tolist()
    medicacion_ids = df_medicacion['medicacion_id'].tolist()
    diagnostico_ids = df_diagnosticos['diagnostico_id'].tolist()
    
    # Mapear nombres de diagnóstico a IDs para facilitar la selección
    diagnostico_name_to_id = df_diagnosticos.set_index('name')['diagnostico_id'].to_dict()

    # IDs de antipsicóticos para la lógica de peso
    antipsicoticos_ids = df_medicacion[df_medicacion['Droga'].isin(antipsicoticos_list)]['medicacion_id'].tolist()
    
    # Asignación de diagnósticos
    # Esquizofrenia: 34%, Trastorno Bipolar: 27%
    # El resto se distribuye entre TAG, TLP, Depresión
    
    num_esquizofrenia = int(num_pacientes * 0.34)
    num_trastorno_bipolar = int(num_pacientes * 0.27)
    
    remaining_diagnoses_count = num_pacientes - num_esquizofrenia - num_trastorno_bipolar
    
    other_diagnoses = [
        diagnostico_name_to_id["TAG"],
        diagnostico_name_to_id["TLP"],
        diagnostico_name_to_id["Depresion"]
    ]
    
    # Distribución equitativa para los diagnósticos restantes
    num_tag = remaining_diagnoses_count // len(other_diagnoses)
    num_tlp = remaining_diagnoses_count // len(other_diagnoses)
    num_depresion = remaining_diagnoses_count - num_tag - num_tlp
    
    assigned_diagnoses = (
        [diagnostico_name_to_id["Esquizofrenia"]] * num_esquizofrenia +
        [diagnostico_name_to_id["Trastorno Bipolar"]] * num_trastorno_bipolar +
        [diagnostico_name_to_id["TAG"]] * num_tag +
        [diagnostico_name_to_id["TLP"]] * num_tlp +
        [diagnostico_name_to_id["Depresion"]] * num_depresion
    )
    random.shuffle(assigned_diagnoses) # Mezclar para una distribución aleatoria

    # Simular la propensión de algunos profesionales a usar antipsicóticos
    # Seleccionar 3 profesionales "favorables" a antipsicóticos (aprox. 18% del total)
    num_antips_prone_prof = max(1, int(len(profesionales_ids) * 0.18))
    antips_prone_prof_ids = random.sample(profesionales_ids, num_antips_prone_prof)
    
    paciente_counter = 0
    for i in range(1, num_pacientes + 1):
        
        # Asignar un profesional (muchos a uno)
        profesional_id = random.choice(profesionales_ids)
        
        # Asignar un diagnóstico (muchos a uno)
        diagnostico_id = assigned_diagnoses.pop(0) if assigned_diagnoses else random.choice(diagnostico_ids)
        
        # Determinar el número de medicaciones psiquiátricas
        # np.random.normal(media, desvio_estandar)
        num_meds = max(1, int(np.random.normal(3, 1.5))) 
        
        # Seleccionar medicaciones para el paciente
        current_patient_meds = random.sample(medicacion_ids, min(num_meds, len(medicacion_ids)))
        
        # Lógica para la asociación Antipsicóticos y Profesionales
        # Si el profesional es "pro-antipsicóticos", hay más chance de recetar uno.
        if profesional_id in antips_prone_prof_ids and not any(m_id in antipsicoticos_ids for m_id in current_patient_meds):
            # Si el paciente no tiene ya un antipsicótico, agregar uno con mayor probabilidad
            if random.random() < 0.7: # 70% de chance de añadir un antipsicótico si el profesional es pro-antips
                current_patient_meds.append(random.choice(antipsicoticos_ids))
                current_patient_meds = list(set(current_patient_meds)) # Eliminar duplicados
                
        # Asegurarse de que al menos un antipsicótico sea recetado a pacientes con Esquizofrenia
        if diagnostico_id == diagnostico_name_to_id["Esquizofrenia"]:
            if not any(m_id in antipsicoticos_ids for m_id in current_patient_meds):
                current_patient_meds.append(random.choice(antipsicoticos_ids))
                current_patient_meds = list(set(current_patient_meds))

        for medicacion_id in current_patient_meds:
            tratamientos_data.append({
                "paciente_id": i,
                "medicacion_id": medicacion_id,
                "profesionales_id": profesional_id,
                "diagnostico_id": diagnostico_id
            })
            paciente_counter += 1
            
    df_tratamientos = pd.DataFrame(tratamientos_data)
    df_tratamientos.to_csv("../data/Tratamientos.csv", index=False, sep=';')
    print(f"Tratamientos.csv generado con {len(df_tratamientos)} registros.")
    return df_tratamientos

# --- Generación de Metabolico.csv ---
def generate_metabolico_csv(df_tratamientos, df_medicacion, antipsicoticos_list):
    metabolico_data = []
    
    # Obtener los IDs únicos de pacientes
    unique_pacientes_ids = df_tratamientos['paciente_id'].unique()
    
    # Crear un diccionario para saber qué medicaciones toma cada paciente (IDs de medicación)
    paciente_meds_map = df_tratamientos.groupby('paciente_id')['medicacion_id'].apply(list).to_dict()
    
    # IDs de antipsicóticos para la lógica de peso
    antipsicoticos_ids = df_medicacion[df_medicacion['Droga'].isin(antipsicoticos_list)]['medicacion_id'].tolist()

    for paciente_id in unique_pacientes_ids:
        edad = random.randint(20, 65)
        
        # Verificar si el paciente toma algún antipsicótico
        takes_antipsicotic = any(med_id in antipsicoticos_ids for med_id in paciente_meds_map.get(paciente_id, []))
        
        # Simular asociación entre antipsicóticos y aumento de peso
        if takes_antipsicotic:
            # Rango de peso más alto si toma antipsicóticos
            peso = round(random.uniform(70, 110), 1) # Ej: media 90, desvio 10-15
            imc = round(random.uniform(25, 35), 1) # Ej: media 30
        else:
            # Rango de peso normal
            peso = round(random.uniform(55, 85), 1) # Ej: media 70, desvio 5-10
            imc = round(random.uniform(18, 28), 1) # Ej: media 23
            
        metabolico_data.append({
            "paciente_id": paciente_id,
            "edad": edad,
            "peso": peso,
            "imc": imc
        })
        
    df_metabolico = pd.DataFrame(metabolico_data)
    df_metabolico.to_csv("../data/Metabolico.csv", index=False, sep=';')
    print(f"Metabolico.csv generado con {len(df_metabolico)} registros.")
    return df_metabolico

# --- Ejecución de la generación de CSVs ---
if __name__ == "__main__":
    # Asegurarse de que la carpeta 'data' exista
    if not os.path.exists("../data"):
        os.makedirs("../data")
        print("Carpeta '../data' creada.")

    df_profesionales = generate_profesionales_csv()
    df_diagnosticos = generate_diagnosticos_csv()
    df_medicacion, antipsicoticos_list = generate_medicacion_csv() # Obtenemos la lista de antipsicóticos

    # Generamos la nueva tabla Pacientes.csv
    df_pacientes = generate_pacientes_csv()

    # Generamos Tratamientos.csv (antes Pacientes.csv) usando la lista de antipsicóticos
    # Nota: Pasamos df_pacientes para obtener el número correcto de pacientes para la generación de Tratamientos
    df_tratamientos = generate_tratamientos_csv(df_profesionales, df_medicacion, df_diagnosticos, antipsicoticos_list, num_pacientes=len(df_pacientes))

    # Generamos Metabolico.csv usando la lista de antipsicóticos para la lógica de peso
    df_metabolico = generate_metabolico_csv(df_tratamientos, df_medicacion, antipsicoticos_list)

    print("\nTodos los archivos CSV han sido generados exitosamente en la carpeta '../data/'.")