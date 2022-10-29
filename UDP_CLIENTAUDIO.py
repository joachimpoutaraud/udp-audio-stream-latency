import socket
import pyaudio, time
from threading import Thread
from multiprocessing import Queue


class Client:

    def __init__(self, client_port=30002, server_ip="127.0.0.1", server_port=30001, sr=48000, buffer_size=1024, bitres=16, channels=2):

        self.client_ip = socket.gethostbyname(socket.gethostname())
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port
        self.sr = sr

        self.buffer_size = buffer_size
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels
		
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPClientSocket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF, self.audio_buffer)
        self.UDPClientSocket.bind((self.client_ip, self.client_port))

        self.record = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=self.channels, rate=self.sr, output=True, frames_per_buffer=self.buffer_size)
        self.play = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=self.channels, rate=self.sr, input=True, frames_per_buffer=self.buffer_size)

        self.q = Queue()

    def listen(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate
        
        print('Waiting for connection...', (self.client_ip, (self.client_port)))

        def record(socket, audio_buffer, period):
            i = 0
            while True:
                frame, server_addr = socket.recvfrom(audio_buffer)
                if i == 0:
                    print('Connection from Peer!', server_addr)
                else:
                    self.record.write(frame)
                    time.sleep(period)
                i = 1

        t1 = Thread(target=record, args=(self.UDPClientSocket, self.audio_buffer, period))
        t1.start()
        

    def send(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate

        def play(socket, buffer_size, server_ip, server_port, period):
            while True:
                frame = self.play.read(buffer_size, exception_on_overflow=False) # Ignore overflow IOError
                socket.sendto(frame, (server_ip, server_port))
                time.sleep(period)  

        t1 = Thread(target=play, args=(self.UDPClientSocket, self.buffer_size, self.server_ip, self.server_port, period))
        t1.start()  


client = Client(server_ip="127.0.0.1", sr=48000, buffer_size=1024, bitres=16, channels=2)
t1 = Thread(target=client.listen, args=())
t2 = Thread(target=client.send, args=())
t1.start()
t2.start()