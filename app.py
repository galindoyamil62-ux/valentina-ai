import os
import streamlit as st
import edge_tts
import asyncio
import PyPDF2
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Valentina AI", page_icon="🧠", layout="centered")

# ---------------------------------------------------------------------------
# Estilo — paleta, tipografía y reskin de los componentes nativos de Streamlit
#
# Nota: uso selectores [data-testid="..."] porque son los más estables entre
# versiones de Streamlit. Las clases tipo ".st-emotion-cache-xxxx" cambian en
# cada release y no deben usarse para CSS permanente.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,600&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #150E20;
    --glow-rose: rgba(255, 111, 145, 0.16);
    --glow-mint: rgba(124, 224, 198, 0.12);
    --surface: #1F1730;
    --surface-border: #372755;
    --text-primary: #F3EEFA;
    --text-muted: #A99BC7;
    --accent-rose: #FF6F91;
    --accent-mint: #7CE0C6;
}

html, body, .stApp {
    background:
        radial-gradient(circle at 12% 8%, var(--glow-rose), transparent 42%),
        radial-gradient(circle at 88% 0%, var(--glow-mint), transparent 45%),
        var(--bg) !important;
}
* { font-family: 'Manrope', sans-serif; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* ---- Encabezado ---- */
.valentina-header {
    padding-bottom: 1.6rem;
    margin-bottom: 1.6rem;
    border-bottom: 1px solid var(--surface-border);
}
.valentina-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent-mint);
    margin-bottom: 0.5rem;
}
.valentina-title-row {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 0.5rem;
}
.valentina-title {
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-weight: 600;
    font-size: 2.8rem;
    color: var(--text-primary);
    margin: 0;
    line-height: 1;
}
.valentina-sub {
    color: var(--text-muted);
    font-size: 1rem;
    max-width: 42ch;
    margin: 0;
}

/* ---- Firma visual: ecualizador animado (referencia real a la voz de Valentina) ---- */
.wave { display: flex; align-items: flex-end; gap: 3px; height: 28px; }
.wave span {
    width: 4px;
    border-radius: 2px;
    background: linear-gradient(180deg, var(--accent-rose), var(--accent-mint));
    animation: wave-pulse 1.1s ease-in-out infinite;
}
.wave span:nth-child(1) { height: 40%; animation-delay: 0s; }
.wave span:nth-child(2) { height: 75%; animation-delay: 0.12s; }
.wave span:nth-child(3) { height: 100%; animation-delay: 0.24s; }
.wave span:nth-child(4) { height: 55%; animation-delay: 0.36s; }
.wave span:nth-child(5) { height: 85%; animation-delay: 0.48s; }
@keyframes wave-pulse {
    0%, 100% { transform: scaleY(0.35); opacity: 0.55; }
    50% { transform: scaleY(1); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
    .wave span { animation: none; }
}

/* ---- Burbujas de chat ---- */
[data-testid="stChatMessage"] { padding: 0.3rem 0; }
[data-testid="stChatMessageContent"] {
    background: var(--surface);
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    padding: 0.9rem 1.1rem;
}
[data-testid="stChatMessage"] img {
    border-radius: 50%;
}

/* ---- Adjuntar archivo ---- */
[data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--surface-border);
    border-radius: 14px;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent;
    border: 1px dashed var(--surface-border);
    border-radius: 12px;
}

/* ---- Campo de mensaje ---- */
[data-testid="stChatInput"] textarea {
    background: var(--surface) !important;
    border: 1px solid var(--surface-border) !important;
    border-radius: 999px !important;
    color: var(--text-primary) !important;
}

/* ---- Spinner ---- */
[data-testid="stSpinner"] p {
    color: var(--accent-mint);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.markdown("""
<div class="valentina-header">
    <div class="valentina-eyebrow">Asistente personal · 24/7</div>
    <div class="valentina-title-row">
        <h1 class="valentina-title">Valentina</h1>
        <div class="wave"><span></span><span></span><span></span><span></span><span></span></div>
    </div>
    <p class="valentina-sub">Razona, busca en internet, lee tus archivos y te contesta con voz.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Avatares — pon tu propia imagen en assets/ y se usa automáticamente.
# Nada se genera ni se edita aquí: si existe el archivo, se muestra tal cual.
# ---------------------------------------------------------------------------
ASSETS_DIR = "assets"
VALENTINA_AVATAR_PATH = os.path.join(ASSETS_DIR, "valentina.png")
USER_AVATAR_PATH = os.path.join(ASSETS_DIR, "usuario.png")

def resolve_avatar(path, fallback_emoji):
    return path if os.path.exists(path) else fallback_emoji

avatar_valentina = resolve_avatar(VALENTINA_AVATAR_PATH, "🧠")
avatar_usuario = resolve_avatar(USER_AVATAR_PATH, "🙂")

# ---------------------------------------------------------------------------
# Llave de Groq
# ---------------------------------------------------------------------------
groq_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

if not groq_key:
    st.error("Falta configurar la GROQ_API_KEY en los secretos de Streamlit.")
    st.stop()

# ---------------------------------------------------------------------------
# Cerebro y herramientas
# ---------------------------------------------------------------------------
llm = ChatGroq(
    api_key=groq_key,
    model_name="openai/gpt-oss-120b",
    temperature=0.2
)
buscador_web = DuckDuckGoSearchRun()

if "historial" not in st.session_state:
    system_prompt = SystemMessage(content="Tu nombre es VALENTINA. Eres mi asistente de IA personal. Tu objetivo es ayudarme a conseguir resultados. Eres inteligente, directa, analítica y natural. Ve directo al punto. No uses frases genéricas como 'Claro que sí'. Puedes buscar en internet y leer archivos que te envíe.")
    st.session_state.historial = [system_prompt]

# ---------------------------------------------------------------------------
# Adjuntar archivo — colapsado por defecto para no saturar la pantalla
# ---------------------------------------------------------------------------
with st.expander("📎 Adjuntar archivo (PDF o TXT)"):
    archivo_subido = st.file_uploader(
        "Sube un archivo para que Valentina lo lea",
        type=["pdf", "txt"],
        label_visibility="collapsed"
    )

# ---------------------------------------------------------------------------
# Voz
# ---------------------------------------------------------------------------
async def generar_audio(texto):
    archivo_salida = "respuesta.mp3"
    comunicador = edge_tts.Communicate(texto, "es-MX-DaliaNeural")
    await comunicador.save(archivo_salida)
    return archivo_salida

# ---------------------------------------------------------------------------
# Historial en pantalla
# ---------------------------------------------------------------------------
for msg in st.session_state.historial:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar=avatar_usuario):
            st.markdown(msg.content)
    elif not isinstance(msg, SystemMessage):
        with st.chat_message("assistant", avatar=avatar_valentina):
            st.markdown(msg.content)

# ---------------------------------------------------------------------------
# Entrada de texto del usuario
# ---------------------------------------------------------------------------
pregunta_usuario = st.chat_input("Escribe tu mensaje o pídele que investigue algo...")

if pregunta_usuario:
    with st.chat_message("user", avatar=avatar_usuario):
        st.markdown(pregunta_usuario)

    texto_procesado = pregunta_usuario

    if archivo_subido is not None:
        texto_extraido = ""
        if archivo_subido.name.endswith('.pdf'):
            lector = PyPDF2.PdfReader(archivo_subido)
            texto_extraido = "".join([p.extract_text() for p in lector.pages])
        else:
            texto_extraido = archivo_subido.read().decode("utf-8")
        texto_procesado += f"\n\n[Contenido del archivo subido]:\n{texto_extraido[:8000]}"

    if any(palabra in pregunta_usuario.lower() for palabra in ["busca", "investiga", "noticias", "restaurante", "actualidad"]):
        with st.spinner("Buscando en internet..."):
            res_web = buscador_web.run(pregunta_usuario)
            texto_procesado += f"\n\n[Resultados web encontrados]: {res_web}"

    st.session_state.historial.append(HumanMessage(content=texto_procesado))

    with st.chat_message("assistant", avatar=avatar_valentina):
        with st.spinner("Valentina está pensando..."):
            respuesta_ia = llm.invoke(st.session_state.historial)
            texto_respuesta = respuesta_ia.content
            st.markdown(texto_respuesta)

            st.session_state.historial.append(respuesta_ia)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ruta_audio = loop.run_until_complete(generar_audio(texto_respuesta))
                st.audio(ruta_audio, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.warning(f"No se pudo generar el audio: {e}")