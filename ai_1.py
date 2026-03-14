import cv2
import mediapipe as mp
import time
import serial
import os
from datetime import datetime
import requests

# Konfigurasi Telegram Bot
BOT_TOKEN = "8420629251:AAGX00d1Q1MeJiIX7EGMmMqyKahvGK9SjrA"
CHAT_ID = "5521616851"

# Konfigurasi Serial
try:
    ser = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
    print("Terhubung dengan ESP32")
except:
    print("Gagal terhubung dengan ESP32")
    ser = None

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

last_screenshot_time = 0
screenshot_cooldown = 3
monitoring_active = False
last_screenshot_path = ""

def send_telegram_message(message):
    """Mengirim pesan ke Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def send_telegram_photo(photo_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            print("Foto berhasil dikirm ke Telegram")
            return True
        else:
            print(f"Gagal mengirim foto: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending photo: {e}")
        return False

def take_screenshot():
    """Mengambil screenshot dari frame webcam dan mengirim ke Telegram"""
    global last_screenshot_path
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_capture_{timestamp}.png"
        folder_foto = 'D:/Python/Mediapipe/arduino_python/screenshots/'

        # Buat folder screenshot jika belum ada
        if not os.path.exists(folder_foto):
            os.makedirs(folder_foto)
        
        filepath = os.path.join(folder_foto, filename)

        # PERBAIKAN: Gunakan cv2.imwrite untuk menyimpan frame webcam
        success = cv2.imwrite(filepath, frame)
        
        if success:
            print(f"📸 Frame webcam disimpan di: {filepath}")
            
            # PERBAIKAN: Update global variable
            last_screenshot_path = filepath

            # Kirim notifikasi ke ESP32
            if ser and ser.is_open:
                ser.write(f"SCREENSHOT:{filename}\n".encode('utf-8'))
                print(f"📤 Sent to ESP32: SCREENSHOT:{filename}")

            # Langsung kirim foto ke Telegram
            caption = f"📸 Webcam Capture - Gesture Recognition\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📁 {filename}"
            if send_telegram_photo(filepath, caption):
                print("✅ Foto webcam berhasil dikirim ke Telegram")
                send_telegram_message(f"✅ <b>Webcam capture berhasil diambil dan dikirim!</b>\n📁 <code>{filename}</code>")
            else:
                print("❌ Gagal mengirim foto webcam ke Telegram")
                send_telegram_message(f"❌ <b>Webcam capture diambil tapi gagal dikirim</b>\n📁 <code>{filename}</code>")
            
            return filepath
        else:
            print("❌ Gagal menyimpan frame webcam")
            send_telegram_message("❌ <b>Gagal menyimpan frame webcam</b>")
            return None
    
    except Exception as e:
        print(f"❌ Error mengambil screenshot: {e}")
        send_telegram_message(f"❌ <b>Error mengambil webcam capture:</b>\n<code>{str(e)}</code>")
        return None
    
def send_last_photo():
    """Mengirim foto terakhir ke Telegram"""
    global last_screenshot_path
    
    if last_screenshot_path and os.path.exists(last_screenshot_path):
        caption = f"📸 Webcam Capture Terakhir\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if send_telegram_photo(last_screenshot_path, caption):
            send_telegram_message("✅ <b>Foto webcam terakhir berhasil dikirim!</b>")
            return True
        else:
            send_telegram_message("❌ <b>Gagal mengirim foto webcam terakhir</b>")
            return False
    else:
        send_telegram_message("📭 <b>Belum ada webcam capture yang diambil</b>")
        return False
    
def send_gesture_detected(gesture):
    """Mengirim notifikasi gesture terdeteksi ke ESP32"""
    if ser and ser.is_open:
        try:
            if gesture == "peace":
                ser.write(b"PEACE_DETECTED\n")
                print("✌️ Sent: PEACE_DETECTED")
            elif gesture == "thumbs_up":
                ser.write(b"THUMBS_UP_DETECTED\n")
                print("👍 Sent: THUMBS_UP_DETECTED")
        except Exception as e:
            print(f"❌ Error sending gesture: {e}")

def check_serial_commands():
    """Memeriksa perintah dari ESP32"""
    global monitoring_active
    
    if ser and ser.in_waiting > 0:
        try:
            raw_data = ser.readline()
            command = raw_data.decode('utf-8', errors='ignore').strip()
            print(f"📥 Received from ESP32: {command}")

            if command == "START_MONITORING":
                monitoring_active = True
                print("🟢 Monitoring diaktifkan")
                send_telegram_message("🔍 <b>Monitoring Gesture Diaktifkan</b>")

            elif command == "STOP_MONITORING":
                monitoring_active = False
                print("🔴 Monitoring dinonaktifkan")
                send_telegram_message("🛑 <b>Monitoring Gesture Dinonaktifkan</b>")

            elif command == "SEND_LAST_PHOTO":
                print("📤 Mengirim foto terakhir...")
                send_last_photo()
                
        except Exception as e:
            print(f"❌ Error reading serial: {e}")

def is_thumbs_up(hand_landmarks):
    tip_index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
    mcp_index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    tip_middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
    mcp_middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
    tip_ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
    mcp_ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y
    tip_pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y
    mcp_pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y
    tip_thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
    mcp_thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].y

    thumb_up = (tip_thumb < mcp_thumb) and (tip_index > mcp_index) and (tip_middle > mcp_middle) and (tip_ring > mcp_ring) and (tip_pinky > mcp_pinky)
    if thumb_up:
        return True
    return False


def is_peace_sigh(hand_landmarks):
    # Dapatkan koordinat y yang dinormnalisasi untuk landmark utama 
    # Catatan: Nilai Y yang lebih kecil berarti posisi lebih tinggi di layar
    tip_index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
    pip_index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    tip_middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
    pip_middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    tip_ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
    pip_ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
    tip_pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y
    pip_pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP].y

    # Logika: Telunjuk dan tengah di atas ibu jari, lainnya di bawah
    if (tip_index < pip_index and tip_middle < pip_middle and tip_ring > pip_ring and tip_pinky > pip_pinky):
        return True
    return False

cap = cv2.VideoCapture(0)
with mp_hands.Hands(min_detection_confidence=0.5,
                    min_tracking_confidence=0.5) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Cannot read frame")
            break

        # Periksa serial
        check_serial_commands()

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        current_time = time.time()
        gesture_detected = False
        
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                if is_peace_sigh(hand_landmarks):
                    cv2.putText(frame, "Peace - SCREENSHOT!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255,0), 2, cv2.LINE_AA)
                    gesture_detected = "peace"
                elif is_thumbs_up(hand_landmarks):
                    cv2.putText(frame, "Thumbs up - SCEREENSHOT!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255,0), 2, cv2.LINE_AA)
                    gesture_detected = "thumbs_up"

        # Status monitoring
        status_text = "Monitoring: " + ("AKTIF" if monitoring_active else "NONAKTIF")
        status_color = (0, 255, 0) if monitoring_active else (0, 0, 255)
        cv2.putText(frame, status_text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2, cv2.LINE_AA)

        # Info connection status
        connection_status = "ESP32: " + ("TERHUBUNG" if ser else "TIDAK TERHUBUNG")
        cv2.putText(frame, connection_status, (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # ambil screenshots jika gesture terdeteksi
        if (gesture_detected and monitoring_active and (current_time - last_screenshot_time) > screenshot_cooldown):
            send_gesture_detected(gesture_detected)
            filename = take_screenshot()

            if filename:
                cv2.putText(frame, "SCREENSHOT & SEND!", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                last_screenshot_time = current_time

        cv2.imshow('Hand Gesture Recognition', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
if ser:
    ser.close()
    print("🔌 Serial connection closed")