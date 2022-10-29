import socket
import pyaudio, time
from threading import Thread
from multiprocessing import Queue


class Server:

    def __init__(self, server_port=30001, client_ip="127.0.0.1", client_port=30002, sr=48000, buffer_size=1024, bit_resolution=16, channels=2):

        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.sr = sr
        self.buffer_size = buffer_size
        self.audio_buffer = int((bit_resolution / 8) * channels * buffer_size)
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
        
        print('Waiting for connection...', (self.server_ip, (self.server_port)))

        def record(socket, audio_buffer, period):
            i = 0
            while True:
                frame, client_addr = socket.recvfrom(audio_buffer)
                if i == 0:
                    print('Connection from Peer!', client_addr)
                else:
                    self.record.write(frame)
                    time.sleep(period)
                i = 1

        t1 = Thread(target=record, args=(self.UDPServerSocket, self.audio_buffer, period))
        t1.start()
        

    def send(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate

        def play(socket, buffer_size, client_ip, client_port, period):
            while True:
                frame = self.play.read(buffer_size, exception_on_overflow=False) # Ignore overflow IOError
                socket.sendto(frame, (client_ip, client_port))
                time.sleep(period)  

        t1 = Thread(target=play, args=(self.UDPServerSocket, self.buffer_size, self.client_ip, self.client_port, period))
        t1.start()      
            
           
server = Server(client_ip="127.0.0.1", sr=48000, buffer_size=1024, bit_resolution=16, channels=2)
t1 = Thread(target=server.listen, args=())
t2 = Thread(target=server.send, args=())
t1.start()
t2.start()

