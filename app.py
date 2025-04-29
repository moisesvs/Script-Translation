import streamlit as st
import os
import feedparser
import yt_dlp
import whisper
import ffmpeg
import re
import unicodedata
from fpdf import FPDF
from transformers import pipeline
import smtplib
from email.message import EmailMessage
import tempfile

# --- CONFIGURACIÓN ---
EMAIL = "moisesvs@gmail.com"
EMAIL_PASS = "odeogoweqnzhqsuf"
CHANNEL_ID = "UC2q5P9JVoA6N8mE622gRP7w"
# ----------------------

st.set_page_config(page_title="YouTube a PDF", layout="centered")
st.title("📺 Transcripción + Resumen + PDF")
st.write("Sube tu archivo `cookies.txt` para procesar el último video del canal y generar el PDF con resumen y transcripción. El resultado será enviado por correo a moisesvs@gmail.com.")

# Subir cookies.txt
cookies_file = st.file_uploader("📤 Sube cookies.txt", type="txt")

# Mostrar mensaje inicial
if not cookies_file:
    st.warning("📂 Por favor, sube tu archivo `cookies.txt` para continuar.")
    st.stop()

# Procesar
if st.button("🎬 Procesar video"):
    with st.spinner("Procesando..."):

        # --- FUNCIONES AUXILIARES ---
        def limpiar_texto(texto):
            return ''.join(c for c in texto if ord(c) < 256 and unicodedata.category(c)[0] != 'C')

        def limpiar_para_resumen(texto):
            return ''.join(c for c in texto if unicodedata.category(c)[0] != 'C' and ord(c) < 256).strip()

        def obtener_ultimo_video(channel_id):
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                try:
                    with yt_dlp.YoutubeDL({
                        'quiet': True,
                        'skip_download': True,
                        'cookiefile': tmp_cookie_path,
                        'user_agent': 'Mozilla/5.0',
                        'http_headers': {'Accept-Language': 'en-US,en;q=0.9'}
                    }) as ydl:
                        ydl.extract_info(entry.link, download=False)
                    return entry.link, entry.title
                except:
                    continue
            raise Exception("❌ No se encontró ningún video accesible.")

        def descargar_audio(video_url, output_path):
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'cookiefile': tmp_cookie_path,
                'quiet': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return output_path.replace("%(ext)s", "mp3")

        def convertir_a_wav(input_path, output_path):
            ffmpeg.input(input_path).output(output_path, ac=1, ar='16k').run(overwrite_output=True, quiet=True)
            return output_path

        def transcribir_audio(wav_path):
            model = whisper.load_model("base")
            return model.transcribe(wav_path)["text"]

        def resumir_transcripcion(texto):
            texto = limpiar_para_resumen(texto)
            if len(texto.split()) < 50:
                return "El contenido del video es muy breve para resumirlo."
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

        # --- FLUJO PRINCIPAL ---
        tmp_cookie = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp_cookie.write(cookies_file.read())
        tmp_cookie.close()
        tmp_cookie_path = tmp_cookie.name

        video_url, titulo = obtener_ultimo_video(CHANNEL_ID)
        st.success(f"🎥 Video detectado: {titulo}")

        mp3_path = os.path.join(tempfile.gettempdir(), "audio.mp3")
        mp3_path = descargar_audio(video_url, mp3_path)

        wav_path = os.path.join(tempfile.gettempdir(), "audio.wav")
        convertir_a_wav(mp3_path, wav_path)

        transcripcion = transcribir_audio(wav_path)
        resumen = resumir_transcripcion(transcripcion)
        pdf_path = crear_pdf(transcripcion, resumen, titulo)

        enviar_email("✅ Transcripción completa", f"🎥 {titulo}\n\n📝 Transcripción:\n\n{transcripcion}")
        enviar_email("📄 PDF generado", f"🎥 {titulo}\n\n📄 Resumen:\n\n{resumen}", pdf_path=pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("📥 Descargar PDF", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf")
        st.success("✅ Todo listo. El PDF fue enviado por correo y está disponible para descarga.")
