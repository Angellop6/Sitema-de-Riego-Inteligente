from openai import OpenAI
import os
import json
import re
 
client = OpenAI(
    base_url=os.getenv("HUGGINGFACE_BASE_URL"),
    api_key=os.getenv("HUGGINGFACE_API_KEY")
) 
prompt = """
You are a plant care assistant.
I will give you a plant and its humidity reading.
Your task:
1. Return *only a JSON object* with a field "humidity" (ideal percentage).
2. Provide a *very short care tip* in one line in the field "care".
3. Do *not add any extra text*.
 
Example format:
{
  "humidity": 55,
  "care": "The plant should be in partial light."
}
 
Question: What is the ideal humidity level for a bougainvillea?
Respond in the exact JSON format.
"""
 
completion = client.chat.completions.create(
    model="HuggingFaceTB/SmolLM3-3B:hf-inference",
    messages=[{"role": "user", "content": prompt}],
)
 



texto = completion.choices[0].message.content

# Expresión regular para encontrar un JSON (texto entre llaves)
patron_json = r'\{.*?\}'

# Buscar todas las coincidencias que tengan el patrón
coincidencias = re.findall(patron_json, texto, re.DOTALL)

# Convertir la primera coincidencia válida a diccionario
for c in coincidencias:
    try:
        diccionario = json.loads(c)
        # Imprimir el JSON completo
        print("JSON encontrado y convertido a diccionario:")
        print(diccionario)
        
        # Imprimir campos por separado
        print("\nCampos por separado:")
        print("Humedad ideal:", diccionario.get("humidity"))
        print("Cuidado:", diccionario.get("care"))
        
        break  # Salir después de encontrar el primer JSON válido
    except json.JSONDecodeError:
        continue