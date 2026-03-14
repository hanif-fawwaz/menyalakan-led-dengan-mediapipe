import serial
import cv2
import mediapipe as mp
import math
import time

ser = serial.Serial('COM5', 9600, timeout=1)
time.sleep(2)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# DataFrame untuk menyimpan hasil
# df = pd.DataFrame(columns=['Timestamp', 'Distance_index', 'angle_index'])

cap = cv2.VideoCapture(0)

with mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        h, w, c = frame.shape

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Ambil koordinat jari jempol (id=4) dan telunjuk (id=8)
                thumb = hand_landmarks.landmark[4]
                index = hand_landmarks.landmark[8]

                x1, y1 = int(thumb.x  * w), int(thumb. y * h)
                x2, y2 = int(index. x * w), int(index. y * h)

                # Hitung jarak Euclidean
                distance = math.hypot(x2 - x1, y2 - y1)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Jarak: {int(distance)}", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                if distance < 40:
                    ser.write(b'ON\n')
                    cv2.putText(frame, "LED: ON", (10, 80),
                                cv2.FONT_HERSHEY_SIMPLEX,1, (0, 0, 255), 2)
                    
                else:
                    ser.write(b'OFF\n')
                    cv2.putText(frame, "LED: OFF", (10, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                

            cv2.imshow("Analisis koordinat (jarak dan sudut)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

cap.release()
cv2.destroyAllWindows()