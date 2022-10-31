import socket
import pyaudio, time
from threading import Thread
from multiprocessing import Queue


HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)

class Server:

    def __init__(self, server_port=30001, client_ip="127.0.0.1", client_port=30002, sr=48000, buffer_size=1024, bitres=16, channels=2):

        self.server_ip = "0.0.0.0" # socket.gethostbyname(socket.gethostname())
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        
        self.sr = sr
        self.buffer_size = buffer_size
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF, self.audio_buffer)
        self.UDPServerSocket.bind((self.server_ip, self.server_port))

        self.record = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=self.channels, rate=self.sr, output=True, frames_per_buffer=self.buffer_size)
        self.play = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=self.channels, rate=self.sr, input=True, frames_per_buffer=self.buffer_size)
        
        self.q = Queue()


    def listen(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate
        stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=self.channels, rate=self.sr, output=True, frames_per_buffer=self.buffer_size)
        
        print('Waiting for connection...', (self.server_ip, (self.server_port)))

        def record(audio_buffer, period):
            
            i = 0
            while True:
                frame, client_addr = self.UDPServerSocket.recvfrom(HEADER_SIZE + audio_buffer)

                current_time = time.time_ns()
                packet_index = int.from_bytes(frame[:4], 'big')
                send_time = int.from_bytes(frame[4:12], 'big')
                self.q.put((packet_index, send_time - current_time))

                if i == 0:
                    print('Connection from Peer!', client_addr)
                elif packet_index == 0:
                    break
                else:
                    self.record.write(frame[12:])
                    time.sleep(period)
                i = 1

        t1 = Thread(target=record, args=(self.audio_buffer, period))
        t1.start()
        

    def send(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate


        def play(buffer_size, period):
            
            while True:
                frame = self.play.read(buffer_size, exception_on_overflow=False) # Ignore overflow IOError

                packet_index, time_diff = self.q.get()
                index_bytes = packet_index.to_bytes(4, 'big')
                current_time = time.time_ns()
                time_bytes = (current_time + time_diff).to_bytes(8, 'big')
                frame = index_bytes + time_bytes + frame

                self.UDPServerSocket.sendto(frame, (self.client_ip, self.client_port))
                time.sleep(period)      

        t1 = Thread(target=play, args=(self.buffer_size, period))
        t1.start()      


if __name__ == "__main__":

    server = Server(client_ip="127.0.0.1", sr=48000, buffer_size=1024, channels=1)

    t1 = Thread(target=server.listen, args=())
    t2 = Thread(target=server.send, args=())
    t1.start()
    t2.start()

