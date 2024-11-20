from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import time
import os
import subprocess
from flask_socketio import SocketIO
import threading

from utils import emitir_deteccoes

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Configurações do YOLO e da captura de vídeo
ip = "192.168.202.157"
esp32_url = f"http://{ip}:81/stream"
model = YOLO("best.pt")

frames_interval = 5  # Intervalo de frames para realizar a detecção
frame_count = 0

# Configuração do FFmpeg para HLS
hls_output_dir = "hls_stream"
hls_playlist = os.path.join(hls_output_dir, "stream.m3u8")

# Variável global para gerenciar o processo do FFmpeg192.168.202.157
ffmpeg_process = None

# caminho para o FFMPeg 
ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe")
if not os.path.isfile(ffmpeg_path):
    raise FileNotFoundError(f"O FFmpeg não foi encontrado em: {ffmpeg_path}")

# Função para processar frames com o YOLO
def process_frame(img):
    global frame_count
    frame_count += 1

    # Realiza a detecção a cada 'frames_interval' frames
    if frame_count % frames_interval == 0:
        results = model(img, conf=0.90, verbose=False)
        img = results[0].plot()
        # emitir_deteccoes(results, socketio)
    return img


# Função para iniciar a captura do stream e processar com o FFmpeg
def start_hls_stream():
    global ffmpeg_process

    # Certifique-se de que o diretório HLS existe
    if not os.path.exists(hls_output_dir):
        os.makedirs(hls_output_dir)

    # Captura inicial do vídeo
    cap = cv2.VideoCapture(esp32_url)
    if not cap.isOpened():
        raise ConnectionError("Erro ao conectar com a câmera ESP32-CAM.")

    # Loop para capturar e processar frames em tempo real
    def capture_and_process():
        while True:
            success, frame = cap.read()
            if not success:
                print("Erro ao capturar frame. Tentando reconectar...")
                time.sleep(5)
                cap.open(esp32_url)
                continue

            frame = cv2.resize(frame, (640, 640))
            frame = process_frame(frame)  # Aqui você processa o frame (YOLO, etc.)

            # Salva o frame processado em um arquivo temporário
            temp_file = os.path.join(hls_output_dir, "temp_frame.jpg")
            if not cv2.imwrite(temp_file, frame):
                print("Erro ao salvar frame no arquivo temp_frame.jpg")
                break  # Sai do loop se não conseguir salvar

    # Inicia a thread de captura e processamento
    capture_thread = threading.Thread(target=capture_and_process, daemon=True)
    capture_thread.start()

    # Comando FFmpeg para criar a stream HLS
    ffmpeg_cmd = [
        ffmpeg_path,
        "-re",  # Trata a entrada como um stream em tempo real
        "-loop", "1",  # Loop para o último frame gerado, até que o próximo esteja disponível
        "-i", os.path.join(hls_output_dir, "temp_frame.jpg"),  # Entrada do frame
        "-r", "15",
        "-vf", "scale=640:640",  # Garante a resolução de saída
        "-c:v", "libx264",  # Codec H.264
        "-threads", "6",
        "-preset", "ultrafast",  # Preset rápido
        "-g", "30",  # Intervalo de keyframes (o dobro do FPS)
        "-hls_time", "2",  # Segmentos de 2 segundos
        "-hls_list_size", "5",  # Mantém no máximo 5 segmentos no playlist
        "-hls_flags", "delete_segments",  # Remove segmentos antigos
        "-hls_segment_filename", os.path.join(hls_output_dir, "segment_%03d.ts"),
        os.path.join(hls_output_dir, "stream.m3u8"),
    ]

    # Inicia o processo FFmpeg
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print("FFmpeg iniciado com sucesso")
    except Exception as e:
        print(f"Erro ao iniciar o FFmpeg: {e}")

    # Monitore os logs do FFmpeg
    def monitor_ffmpeg():
        stdout, stderr = ffmpeg_process.communicate()
        print("FFmpeg stdout:", stdout.decode())
        print("FFmpeg stderr:", stderr.decode())

    monitor_thread = threading.Thread(target=monitor_ffmpeg, daemon=True)
    monitor_thread.start()


@app.route("/start_stream", methods=["GET"])
def start_stream():
    """Rota para iniciar a transmissão HLS."""
    global ffmpeg_process

    # Para o stream atual, se necessário
    stop_stream()

    try:
        start_hls_stream()
        return jsonify({"message": "Stream iniciada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stop_stream", methods=["GET"])
def stop_stream():
    """Rota para parar a transmissão."""
    global ffmpeg_process

    if ffmpeg_process:
        ffmpeg_process.terminate()
        ffmpeg_process = None
        return jsonify({"message": "Stream parada com sucesso!"}), 200

    return jsonify({"message": "Nenhum stream ativo para parar."}), 400


@app.route("/camera_stream", methods=["GET"])
def get_stream():
    """Rota para retornar o HLS playlist."""
    if os.path.exists(hls_playlist):
        # Monta a URL do stream HLS manualmente (evitando problemas com `os.path.join`)
        stream_url = f"http://localhost:5000/hls_stream/stream.m3u8"
        return jsonify({"url": stream_url})

    return jsonify({"error": "Stream não encontrada. Inicie a transmissão primeiro."}), 404


@socketio.on("connect")
def handle_connect():
    print("Cliente conectado ao WebSocket.")

# Rota para servir os arquivos HLS
@app.route("/hls_stream/<path:filename>")
def serve_hls_stream(filename):
    return send_from_directory(hls_output_dir, filename)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
