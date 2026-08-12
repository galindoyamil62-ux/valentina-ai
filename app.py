import os
import base64
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
st.set_page_config(page_title="Valentina AI", page_icon="✨", layout="centered")

# ---------------------------------------------------------------------------
# Avatares — pon tu propia imagen en assets/ y se usa automáticamente.
# Nada se genera ni se edita aquí: si existe el archivo, se muestra tal cual.
# Acepta png / jpg / jpeg / webp, así no dependes de un solo formato exacto.
# ---------------------------------------------------------------------------
ASSETS_DIR = "assets"

def encontrar_avatar(nombre_base):
    for ext in ("png", "jpg", "jpeg", "webp"):
        ruta = os.path.join(ASSETS_DIR, f"{nombre_base}.{ext}")
        if os.path.exists(ruta):
            return ruta
    return None

def imagen_a_data_uri(ruta):
    """Convierte una imagen local a data URI base64 para poder inyectarla
    dentro del HTML del encabezado (Streamlit no sirve archivos locales
    directamente como <img src="...">)."""
    ext = os.path.splitext(ruta)[1].lstrip(".").lower()
    mime = "jpeg" if ext == "jpg" else ext
    with open(ruta, "rb") as f:
        datos = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{datos}"

ruta_avatar_valentina = encontrar_avatar("valentina")
ruta_avatar_usuario = encontrar_avatar("usuario")

avatar_valentina = ruta_avatar_valentina or "🧠"
avatar_usuario = ruta_avatar_usuario or "🙂"

# ---------------------------------------------------------------------------
# Estilo — paleta, tipografía y reskin de los componentes nativos de Streamlit
#
# Nota: uso selectores [data-testid="..."] porque son los más estables entre
# versiones de Streamlit. Las clases tipo ".st-emotion-cache-xxxx" cambian en
# cada release y no deben usarse para CSS permanente.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,680;1,9..144,600&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #150E20;
    --glow-rose: rgba(255, 111, 145, 0.16);
    --glow-mint: rgba(124, 224, 198, 0.12);
    --surface: #1F1730;
    --surface-2: rgba(255, 255, 255, 0.03);
    --surface-border: #372755;
    --text-primary: #F3EEFA;
    --text-muted: #A99BC7;
    --accent-rose: #FF6F91;
    --accent-mint: #7CE0C6;
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

html, body, .stApp {
    background:
        radial-gradient(circle at 12% 8%, var(--glow-rose), transparent 42%),
        radial-gradient(circle at 88% 0%, var(--glow-mint), transparent 45%),
        radial-gradient(circle at 50% 100%, rgba(124,224,198,0.05), transparent 55%),
        var(--bg) !important;
}
* { font-family: 'Manrope', sans-serif; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 780px;
    padding-top: 2.75rem;
    padding-bottom: 6rem;
}

/* ---- Scrollbar a medida ---- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--accent-rose), var(--accent-mint));
    border-radius: 8px;
    opacity: 0.5;
}

/* ---- Foco de teclado visible (accesibilidad) ---- */
*:focus-visible {
    outline: 2px solid var(--accent-mint) !important;
    outline-offset: 2px;
}

/* ===========================================================================
   ENCABEZADO — panel de cristal con resplandor ambiental y marca "viva"
   =========================================================================== */
.valentina-header {
    position: relative;
    padding: 1.9rem 2rem;
    margin-bottom: 2rem;
    border-radius: 22px;
    background: linear-gradient(165deg, rgba(255,255,255,0.045), rgba(255,255,255,0.01));
    border: 1px solid var(--surface-border);
    box-shadow: 0 24px 60px -24px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.05);
    overflow: hidden;
}
.valentina-header::after {
    content: "";
    position: absolute;
    top: -60%; left: -8%;
    width: 55%; height: 220%;
    background: radial-gradient(circle, var(--glow-rose), transparent 62%);
    filter: blur(10px);
    pointer-events: none;
}
.valentina-header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.1rem;
    position: relative;
    z-index: 1;
}
.valentina-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent-mint);
}
.valentina-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0.32rem 0.7rem;
    border-radius: 999px;
    border: 1px solid var(--surface-border);
    background: rgba(255,255,255,0.02);
}
.valentina-status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--accent-mint);
    box-shadow: 0 0 8px var(--accent-mint);
    animation: pulso 2.2s ease-in-out infinite;
}
@keyframes pulso { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

.valentina-title-row {
    display: flex;
    align-items: center;
    gap: 1.1rem;
    position: relative;
    z-index: 1;
}
.valentina-title {
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-weight: 600;
    font-size: 2.6rem;
    color: var(--text-primary);
    margin: 0 0 0.3rem 0;
    line-height: 1;
    letter-spacing: -0.01em;
}
.valentina-sub {
    color: var(--text-muted);
    font-size: 0.96rem;
    max-width: 40ch;
    margin: 0;
    line-height: 1.45;
}

/* ---- Marca: foto con anillo degradado en rotación, o ecualizador vivo ---- */
.valentina-mark {
    flex-shrink: 0;
    width: 60px; height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, rgba(255,111,145,0.16), rgba(124,224,198,0.10));
    border: 1px solid var(--surface-border);
}
.valentina-avatar-ring {
    flex-shrink: 0;
    width: 60px; height: 60px;
    border-radius: 50%;
    padding: 2.5px;
    background: conic-gradient(from 0deg, var(--accent-rose), var(--accent-mint), var(--accent-rose));
    animation: girar 7s linear infinite;
}
.valentina-avatar-ring img {
    width: 100%; height: 100%;
    border-radius: 50%;
    object-fit: cover;
    display: block;
    border: 3px solid var(--bg);
}
@keyframes girar { to { transform: rotate(360deg); } }

.wave { display: flex; align-items: flex-end; gap: 3px; height: 24px; }
.wave span {
    width: 3.5px;
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
    .wave span, .valentina-avatar-ring, .valentina-status-dot { animation: none; }
}

/* ===========================================================================
   BURBUJAS DE CHAT — cristal esmerilado con borde de luz degradada
   =========================================================================== */
[data-testid="stChatMessage"] {
    padding: 0.35rem 0;
    animation: mensaje-entra 0.5s var(--ease-out);
}
@keyframes mensaje-entra {
    from { opacity: 0; transform: translateY(10px) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}
[data-testid="stChatMessageContent"] {
    position: relative;
    background: linear-gradient(175deg, rgba(31,23,48,0.78), rgba(21,14,32,0.88));
    backdrop-filter: blur(18px) saturate(150%);
    -webkit-backdrop-filter: blur(18px) saturate(150%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 0.95rem 1.15rem;
    box-shadow: 0 14px 40px -18px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05);
}
[data-testid="stChatMessageContent"]::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: 19px;
    padding: 1px;
    background: linear-gradient(135deg, rgba(255,111,145,0.4), rgba(124,224,198,0.22), transparent 65%);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
}
[data-testid="stChatMessage"] img {
    border-radius: 50%;
    box-shadow: 0 0 0 2px var(--surface-border);
}

/* ===========================================================================
   ADJUNTAR ARCHIVO — tarjeta de cristal con resplandor al pasar el cursor
   =========================================================================== */
[data-testid="stExpander"] {
    background: linear-gradient(175deg, rgba(255,255,255,0.035), rgba(255,255,255,0.008));
    backdrop-filter: blur(16px);
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    transition: border-color 0.3s var(--ease-out), box-shadow 0.3s var(--ease-out);
}
[data-testid="stExpander"]:hover {
    border-color: rgba(255,111,145,0.32);
    box-shadow: 0 0 28px -10px rgba(255,111,145,0.22);
}
[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.01em;
    color: var(--text-primary) !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: rgba(124, 224, 198, 0.025);
    border: 1.5px dashed rgba(255,255,255,0.14);
    border-radius: 14px;
    transition: border-color 0.3s var(--ease-out), background 0.3s var(--ease-out);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent-mint);
    background: rgba(124, 224, 198, 0.055);
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stBaseButton-secondary"],
[data-testid="baseButton-secondary"] {
    transition: all 0.25s var(--ease-out) !important;
}
[data-testid="stFileUploaderDropzone"] button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="baseButton-secondary"]:hover {
    border-color: var(--accent-rose) !important;
    box-shadow: 0 0 16px rgba(255,111,145,0.28) !important;
    transform: translateY(-1px);
}

/* ===========================================================================
   CAMPO DE MENSAJE — pastilla de cristal con resplandor al enfocar
   =========================================================================== */
[data-testid="stChatInput"] {
    background: transparent !important;
}
[data-testid="stChatInput"] textarea {
    background: rgba(31,23,48,0.75) !important;
    backdrop-filter: blur(14px);
    border: 1px solid var(--surface-border) !important;
    border-radius: 999px !important;
    color: var(--text-primary) !important;
    transition: border-color 0.25s var(--ease-out), box-shadow 0.25s var(--ease-out);
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(255,111,145,0.55) !important;
    box-shadow: 0 0 0 3px rgba(255,111,145,0.12), 0 0 26px rgba(255,111,145,0.16) !important;
}
[data-testid="stChatInputSubmitButton"] {
    transition: filter 0.25s var(--ease-out), transform 0.25s var(--ease-out);
}
[data-testid="stChatInputSubmitButton"]:hover {
    filter: drop-shadow(0 0 8px var(--accent-rose));
    transform: scale(1.08);
}

/* ---- Spinner ---- */
[data-testid="stSpinner"] p {
    color: var(--accent-mint);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
}

/* ---- Reproductor de audio ---- */
[data-testid="stAudio"] {
    margin-top: 0.8rem;
    padding: 0.4rem;
    border-radius: 14px;
    border: 1px solid var(--surface-border);
    background: rgba(255,255,255,0.02);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Encabezado — usa la foto de Valentina si existe en assets/, si no muestra
# el ecualizador animado como marca visual por defecto.
# ---------------------------------------------------------------------------
if ruta_avatar_valentina:
    marca_html = (
        f'<div class="valentina-avatar-ring">'
        f'<img src="{imagen_a_data_uri(ruta_avatar_valentina)}" alt="Valentina"></div>'
    )
else:
    marca_html = (
        '<div class="valentina-mark"><div class="wave">'
        '<span></span><span></span><span></span><span></span><span></span>'
        '</div></div>'
    )

st.markdown(f"""
<div class="valentina-header">
    <div class="valentina-header-top">
        <span class="valentina-eyebrow">Asistente personal</span>
        <span class="valentina-status"><span class="valentina-status-dot"></span>En línea</span>
    </div>
    <div class="valentina-title-row">
        {marca_html}
        <div>
            <h1 class="valentina-title">Valentina</h1>
            <p class="valentina-sub">Razona, busca en internet, lee tus archivos y te contesta con voz.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

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
