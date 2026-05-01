"""
🔊 Tannoy Audio Playback (Streamlit)

Web-based interface for uploading and broadcasting WAV audio files
to a multicast Tannoy system using RTP (G.711 µ-law).

Features:
- Upload WAV files via browser
- Multicast audio using FFmpeg
- Select target scope (All / Internal / External / Test)
- Play / Stop audio streams per target
- Delete uploaded files
- Tracks active FFmpeg processes per multicast target
- Logs FFmpeg output to file

Requirements:
- Python 3
- Streamlit
- FFmpeg installed at /usr/bin/ffmpeg
- Vlans require PIM and Multicast routing 

Storage:
- Audio files saved to ~/streamlit/audio_uploads
- Logs written to /home/user/streamlit/ffmpeg.log

Notes:
- Only one active stream per target
- Designed for multicast-enabled networks (IGMP/PIM)
- Uses RTP with G.711 µ-law (8kHz, mono)
 
"""

import streamlit as st
import subprocess
from pathlib import Path

# -----------------------
# Configuration
# -----------------------

BASE_DIR = Path.home() / "streamlit"
AUDIO_DIR = BASE_DIR / "audio_uploads"
AUDIO_DIR.mkdir(exist_ok=True)

FFMPEG_BINARY = "/usr/bin/ffmpeg"

MULTICAST_TARGETS = {
    "All": "239.0.0.1:5004",
    "Internal": "239.0.0.2:5004",
    "External": "239.0.0.3:5004",
    "Test": "239.0.0.0:5004",
}

# -----------------------
# Page setup
# -----------------------

st.set_page_config(
    page_title="Tannoy",
    layout="wide"
)

st.title("🔊 Tannoy Audio Playback")

st.markdown(
    """
Upload **WAV** files and multicast them to the Tannoy system using **RTP (G.711 µ-law)**.
"""
)

# -----------------------
# Session state
# -----------------------

if "ffmpeg_processes" not in st.session_state:
    st.session_state.ffmpeg_processes = {}

# -----------------------
# Target selection (default = Test)
# -----------------------

scope = st.selectbox(
    "Target device scope",
    list(MULTICAST_TARGETS.keys()),
    index=list(MULTICAST_TARGETS.keys()).index("Test")
)

target = MULTICAST_TARGETS[scope]
st.info(f"Streaming target: rtp://{target}")

# -----------------------
# File upload
# -----------------------

uploaded = st.file_uploader(
    "Upload WAV file",
    type=["wav"]
)

if uploaded:
    dest = AUDIO_DIR / uploaded.name
    with open(dest, "wb") as f:
        f.write(uploaded.getbuffer())
    st.success(f"Uploaded: {uploaded.name}")

# -----------------------
# Helper functions
# -----------------------

def play_multicast(file_path: Path, target: str):
    existing = st.session_state.ffmpeg_processes.get(target)
    if existing and existing.poll() is None:
        existing.terminate()

    cmd = [
        FFMPEG_BINARY,
        "-re",
        "-i", str(file_path),
        "-ac", "1",
        "-ar", "8000",
        "-c:a", "pcm_mulaw",
        "-f", "rtp",
        f"rtp://{target}",
    ]

    log_file = open("/home/user/streamlit/ffmpeg.log", "ab")

    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True
    )

    st.session_state.ffmpeg_processes[target] = proc


def stop_multicast(target: str):
    proc = st.session_state.ffmpeg_processes.get(target)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()
        del st.session_state.ffmpeg_processes[target]


def list_audio_files():
    return sorted(AUDIO_DIR.glob("*.wav"))

# -----------------------
# File list
# -----------------------

st.subheader("Available Audio Files")

files = list_audio_files()

if not files:
    st.warning("No audio files uploaded.")
else:
    for f in files:
        c1, c2, c3, c4 = st.columns([5, 2, 2, 2])

        with c1:
            st.write(f.name)

        with c2:
            if st.button("▶ Play", key=f"play_{f.name}"):
                play_multicast(f, target)
                st.success(f"Playing {f.name} to {scope}")

        with c3:
            if st.button("⏹ Stop", key=f"stop_{f.name}"):
                stop_multicast(target)
                st.warning(f"Stopped audio on {scope}")

        with c4:
            if st.button("🗑 Delete", key=f"del_{f.name}"):
                f.unlink(missing_ok=True)
                st.rerun()
