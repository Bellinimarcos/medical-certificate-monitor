import google.generativeai as genai
import os

# --- IMPORTANTE: Substitua abaixo pela sua chave que você copiou ---
MINHA_CHAVE = "AIzaSyBdn82NypGdS1vHuuDdr5MlX9w7MK0U9jo"

genai.configure(api_key=MINHA_CHAVE)

print("\n🔍 PERGUNTANDO AO GOOGLE QUAIS MODELOS ESTÃO DISPONÍVEIS...\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # Mostra o nome exato que precisamos colocar no app.py
            print(f"👉 NOME PARA O CÓDIGO: {m.name}") 
            print(f"   (Nome comercial: {m.displayName})")
            print("-" * 40)
except Exception as e:
    print(f"❌ Erro: {e}")