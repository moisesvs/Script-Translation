import streamlit as st
import os

st.set_page_config(page_title="Subida de cookies.txt", layout="centered")
st.title("📂 Verificador de cookies.txt")

# Subir cookies.txt
cookies_file = st.file_uploader("📤 Sube tu archivo cookies.txt", type="txt")


# Mostrar mensaje si no hay archivo
if not cookies_file:
    st.info("Esperando que subas tu archivo cookies.txt...")
    st.stop()

# Guardar el archivo en el sistema de archivos
try:
    with open("cookies.txt", "wb") as f:
        f.write(cookies_file.read())
    st.success("✅ Archivo cookies.txt subido y guardado correctamente.")
    
    # Mostrar contenido (primeras líneas) como verificación
    with open("cookies.txt", "r") as f:
        contenido = f.read().splitlines()
        st.code("\n".join(contenido[:10]), language='text')
        st.info("✅ Mostrando primeras 10 líneas del archivo.")

    # Verificar si contiene SID (como prueba de validez básica)
    if any("SID" in linea for linea in contenido):
        st.success("🧠 El archivo contiene la cookie SID (¡todo bien!).")
    else:
        st.warning("⚠️ El archivo no contiene la cookie SID. ¿Seguro que lo exportaste correctamente?")
except Exception as e:
    st.error(f"❌ Ocurrió un error al guardar o procesar el archivo: {e}")
