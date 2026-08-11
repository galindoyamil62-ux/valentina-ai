import os
import streamlit as st
import edge_tts
import asyncio
import PyPDF2
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun

# Configuración de la página web
st.set_page_title_config = st.set_page_config(page_title="Valentina AI", page_icon="🧠")

st.title("🧠 Valentina AI — Asistente Personal")
st.write("Tu asistente 24/7 con razonamiento, búsqueda web y voz neuronal.")

# Obtener la llave de Groq de forma segura desde los secretos de Streamlit (o variable de entorno)
groq_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

if not groq_key:
    st.error("Falta configurar la GROQ_API_KEY en los secretos de Streamlit.")
    st.stop()

# Inicializar cerebro y herramientas
llm = ChatGroq(
    api_key=groq_key,
    model_name="llama-3.1-70b-versatile",
    temperature=0.2
)
buscador_web = DuckDuckGoSearchRun()

# Memoria de chat en la sesión de Streamlit
if "historial" not in st.session_state:
    system_prompt = SystemMessage(content="Tu nombre es VALENTINA. Eres mi asistente de IA personal. Tu objetivo es ayudarme a conseguir resultados. Eres inteligente, directa, analítica y natural. Ve directo al punto. No uses frases genéricas como 'Claro que sí'. Puedes buscar en internet y leer archivos que te envíe.")
    st.session_state.historial = [system_prompt]

# Componente para subir archivos (PDF o TXT)
archivo_subido = st.file_uploader("Sube un archivo (PDF o TXT) para que Valentina lo lea", type=["pdf", "txt"])

# Función para generar voz gratuita con Edge-TTS
async def generar_audio(texto):
    archivo_salida = "respuesta.mp3"
    comunicador = edge_tts.Communicate(texto, "es-MX-DaliaNeural") # Voz femenina natural
    await comunicador.save(archivo_salida)
    return archivo_salida

# Mostrar historial de mensajes en pantalla
for msg in st.session_state.historial:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif not isinstance(msg, SystemMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# Entrada de texto del usuario
pregunta_usuario = st.chat_input("Escribe tu mensaje o pídele que investigue algo...")

if pregunta_usuario:
    with st.chat_message("user"):
        st.markdown(pregunta_usuario)
    
    texto_procesado = pregunta_usuario

    # Si hay un archivo subido, extraer su texto
    if archivo_subido is not None:
        texto_extraido = ""
        if archivo_subido.name.endswith('.pdf'):
            lector = PyPDF2.PdfReader(archivo_subido)
            texto_extraido = "".join([p.extract_text() for p in lector.pages])
        else:
            texto_extraido = archivo_subido.read().decode("utf-8")
        texto_procesado += f"\n\n[Contenido del archivo subido]:\n{texto_extraido[:8000]}"

    # Si la petición requiere búsqueda web, ejecutarla automáticamente
    if any(palabra in pregunta_usuario.lower() for palabra in ["busca", "investiga", "noticias", "restaurante", "actualidad"]):
        with st.spinner("Buscando en internet..."):
            res_web = buscador_web.run(pregunta_usuario)
            texto_procesado += f"\n\n[Resultados web encontrados]: {res_web}"

    st.session_state.historial.append(HumanMessage(content=texto_procesado))

    # Generar respuesta con la IA
    with st.chat_message("assistant"):
        with st.spinner("Valentina está pensando..."):
            respuesta_ia = llm.invoke(st.session_state.historial)
            texto_respuesta = respuesta_ia.content
            st.markdown(texto_respuesta)
            
            st.session_state.historial.append(respuesta_ia)

            # Generar y reproducir audio de voz
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ruta_audio = loop.run_until_complete(generar_audio(texto_respuesta))
                st.audio(ruta_audio, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.warning(f"No se pudo generar el audio: {e}")