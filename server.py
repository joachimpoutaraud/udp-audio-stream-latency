import socket
import time
from threading import Thread
from multiprocessing import Queue
import sounddevice as sd


HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)

class Server:

    def __init__(self, 
                server_ip="0.0.0.0",
                server_port=30001, 
                client_ip="127.0.0.1", 
                client_port=30002, 
                sr=48000, 
                buffer_size=256, 
                bitres=16, 
                channels=2,
                device=None, 
                verbose=False, 
                stream=False):

        self.server_ip = server_ip # socket.gethostbyname(socket.gethostname())
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port

        if device:
            print(sd.query_devices())
            print("\nSelect sound device:")
            self.device = input()
        else:
            self.device = None
        
        self.sr = sr
        self.buffer_size = buffer_size
        self.bitres = bitres
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels
        self.verbose = verbose
        self.stream = stream

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF, self.audio_buffer)
        self.UDPServerSocket.bind((self.server_ip, self.server_port))
        
        self.q = Queue()


    def listen(self):
        
        print('Waiting for connection...', (self.server_ip, (self.server_port)))

        def record():

            stream = sd.RawOutputStream(samplerate=self.sr, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
            stream.start()
            
            i = 0
            while True:

                frame, client_addr = self.UDPServerSocket.recvfrom(HEADER_SIZE + self.audio_buffer)

                current_time = time.time_ns()
                packet_index = int.from_bytes(frame[:4], 'big')
                send_time = int.from_bytes(frame[4:12], 'big')
                self.q.put((packet_index, send_time - current_time))

                if i == 0:
                    print('Connection from Peer!', client_addr)
                elif packet_index == 0:
                    break
                else:
                    if self.stream:
                        stream.write(frame[12:])
                i = 1

        t1 = Thread(target=record, args=())
        t1.start()
        

    def send(self):

        payload_size = self.audio_buffer - HEADER_SIZE
        frame = b''.join([b'\x00'] * (payload_size))

        stream = sd.RawInputStream(samplerate=self.sr, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()
        
        while True:

            if self.stream:
                frame = stream.read(self.buffer_size)[0]

            packet_index, time_diff = self.q.get()
            index_bytes = packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            time_bytes = (current_time + time_diff).to_bytes(8, 'big')
            packet = index_bytes + time_bytes + frame

            self.UDPServerSocket.sendto(packet, (self.client_ip, self.client_port))

            if packet_index == 0:
                break

            if self.verbose:
                print(f'|  Server: {self.server_port}  |  Packet received from Client: {packet_index}  |  Packet send at time (ns): {current_time}  |')   
             


if __name__ == "__main__":

    server = Server(client_ip="127.0.0.1", sr=22050, buffer_size=256, channels=2, bitres=32, device=False, stream=True, verbose=False)
    
    t1 = Thread(target=server.listen, args=())
    t2 = Thread(target=server.send, args=())
    t1.start()
    t2.start()