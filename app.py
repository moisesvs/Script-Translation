import streamlit as st
import os
import whisper
import ffmpeg
import re
import unicodedata
from fpdf import FPDF
from transformers import pipeline
import smtplib
from email.message import EmailMessage
import tempfile

EMAIL = "moisesvs@gmail.com"
EMAIL_PASS = "odeogoweqnzhqsuf"

st.set_page_config(page_title="Transcriptor desde Audio", layout="centered")
st.title("🎧 Transcribe tu audio y genera un PDF")

# Subida de archivo de audio
audio_file = st.file_uploader("📤 Sube un archivo de audio (.mp3, .webm, .m4a, etc)", type=["mp3", "webm", "m4a", "wav"])

if not audio_file:
    st.info("Sube un archivo de audio para comenzar.")
    st.stop()

# Campo para el título (opcional)
titulo = st.text_input("✏️ Título del video o audio", value="Transcripción sin título")

if st.button("🚀 Procesar audio"):
    with st.spinner("Procesando..."):

        def limpiar_texto(texto):
            return ''.join(c for c in texto if ord(c) < 256 and unicodedata.category(c)[0] != 'C')

        def limpiar_para_resumen(texto):
            return ''.join(c for c in texto if unicodedata.category(c)[0] != 'C' and ord(c) < 256).strip()

        def convertir_a_wav(input_path, output_path):
            ffmpeg.input(input_path).output(output_path, ac=1, ar='16k').run(overwrite_output=True, quiet=True)
            return output_path

        def transcribir_audio(wav_path):
            model = whisper.load_model("base")
            return model.transcribe(wav_path)["text"]

        def resumir_transcripcion(texto):
            texto = limpiar_para_resumen(texto)
            if len(texto.split()) < 50:
                return "El contenido del audio es muy breve para resumirlo."
            try:
                resumen_pipeline = pipeline("summarization", model="facebook/bart-large-cnn")
                for max_chars in [3500, 2500, 1500]:
                    try:
                        entrada = texto[:max_chars]
                        entrada = entrada[:entrada.rfind(" ")]
                        return resumen_pipeline(entrada, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
                    except:
                        continue
                return texto.split(".")[0] + "..."
            except:
                return "No se pudo generar un resumen automático."

        def crear_pdf(transcripcion, resumen, titulo):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.multi_cell(0, 10, titulo, align="C")
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Resumen:", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, resumen)
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Transcripción completa:", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, transcripcion)
            tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf.output(tmp_pdf.name)
            return tmp_pdf.name

        def enviar_email(asunto, cuerpo, pdf_path=None):
            msg = EmailMessage()
            msg["Subject"] = asunto
            msg["From"] = EMAIL
            msg["To"] = EMAIL
            msg.set_content(cuerpo)
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL, EMAIL_PASS)
                smtp.send_message(msg)

        # Guardar archivo subido
        temp_dir = tempfile.gettempdir()
        input_path = os.path.join(temp_dir, audio_file.name)
        with open(input_path, "wb") as f:
            f.write(audio_file.read())

        # Convertir y procesar
        wav_path = os.path.join(temp_dir, "audio.wav")
        convertir_a_wav(input_path, wav_path)
        transcripcion = transcribir_audio(wav_path)
        resumen = resumir_transcripcion(transcripcion)
        pdf_path = crear_pdf(transcripcion, resumen, titulo)

        enviar_email("✅ Transcripción completa", f"🎧 {titulo}\n\n📝 Transcripción:\n\n{transcripcion}")
        enviar_email("📄 PDF generado", f"🎧 {titulo}\n\n📄 Resumen:\n\n{resumen}", pdf_path=pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("📥 Descargar PDF", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf")
        st.success("✅ PDF enviado por correo y disponible para descarga.")
