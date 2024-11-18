import time
from bson.objectid import ObjectId
from database import get_collection

def save_data_mongodb(result):
    """
    Salva logs de detecção no MongoDB.
    
    :param result: Objeto contendo os resultados da detecção.
    """
    collection = get_collection()
    timestamp = time.time()  # Timestamp atual em segundos
    for box in result.boxes:
        collection.insert_one({
            'activityAuthor': ObjectId('6657690dea6013b6be9e2fde'),
            'activityData': {
                'activityName': 'teste stream cam',
                'activityStart': timestamp,
                'activityEnd': timestamp
            }
        })

def emitir_deteccoes(results, socketio, conf_threshold=0.90):
    """
    Processa os resultados do modelo e emite detecções via SocketIO.

    Args:
        results: Resultados do modelo.
        socketio: Instância do SocketIO.
        conf_threshold: Confiança mínima para considerar a detecção.
    """
    detections = []

    for result in results:
        for box in result.boxes:
            if box.confidence >= conf_threshold:  # Verifica a confiança
                detection_info = {
                    "label": box.label,
                    "confidence": box.confidence,
                    "coordinates": box.xyxy.tolist(),
                }
                detections.append(detection_info)
    
    if detections:
        print("Emitindo detecções:", detections)
        socketio.emit("deteccao", detections)
