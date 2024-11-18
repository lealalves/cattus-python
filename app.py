from flask import Flask, Response
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import time
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
# Configurações do YOLO e da captura de vídeo
ip = "http://192.168.227.157"
esp32_url = f"{ip}:81/stream"
cap = None
model = YOLO("best.pt")

frames_interval = 5  # Intervalo de frames para realizar a detecção
frame_count = 0

# Configurações do MongoDB Atlas
# mongo_uri = "mongodb+srv://cattus-web:ZycXOL2qALXurYW0@cattus-api.sgnegkc.mongodb.net/"
# client = MongoClient(mongo_uri)
# db = client['test']  # Nome do banco de dados
# collection = db['activities']

# Função para abrir o stream da ESP32-CAM
def open_video_stream():
    global cap
    if cap is not None:
        cap.release()
    cap = cv2.VideoCapture(esp32_url)
    if not cap.isOpened():
        print("Erro ao conectar com a câmera ESP32. Tentando novamente...")
        time.sleep(5)  # Espera 5 segundos antes de tentar reconectar
        return open_video_stream()

def save_data_mongodb(result):
    # Salvar logs de detecção no MongoDB
    for box in result.boxes:
        timestamp = time.now
        collection.insert_one({
            'activityAuthor': ObjectId('6657690dea6013b6be9e2fde'),
            'activityData': {
                'activityName': 'teste stream cam',
                'activityStart': timestamp,
                'activityEnd': timestamp
            }
        })

@socketio.on('connect')
def handle_connect():
    print("Cliente conectado ao WebSocket.")
    
# Rota para o stream de vídeo
@app.route('/camera_stream')
def video_feed():
    def generate_frames():
        global frame_count
        open_video_stream()  # Abrir o stream da ESP32-CAM
        while True:
            success, img = cap.read()
            if not success:
                print("Erro na captura do frame. Tentando reconectar...")
                open_video_stream()  # Tenta reconectar se a captura falhar
                continue

            img = cv2.resize(img, (640, 640))
            frame_count += 1
            detections = []

            # Realiza a detecção a cada 'frames_interval' frames
            if frame_count % frames_interval == 0:
                results = model(img, conf=0.90)               

                for result in results:
                    img = result.plot()
                    for box in result.boxes:
                        detection_info = {
                            "label": 'box.label',
                            "confidence": 'box.confidence',
                            "coordinates": 'box.xyxy.tolist()'
                        }
                        detections.append(detection_info)

            if detections:
                print("Emitindo detecções:", detections)
                socketio.emit("deteccao", detections)
            # Codificar o frame como JPEG para enviar via streaming
            ret, buffer = cv2.imencode('.jpg', img)
            img = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    
# Iniciar o servidor Flask
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
