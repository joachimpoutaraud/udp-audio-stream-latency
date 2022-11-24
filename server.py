import socket, time
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
                set_device=False, 
                verbose=False):

        """
        This script is based on the work of Copyright (c) 2021 Chuanyu Xue for measuring udp latency over the network. 
        Contributions are related to streaming audio using sounddevice as well as defining udp packet size and rate in relation to audio stream requirements.

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.

        Args:
            server_ip (str, optional): Defines the server IP address to use. Defaults to "0.0.0.0".
            server_port (int, optional): Defines the server port to use. Defaults to 30001.
            client_ip (str, optional): Defines the client IP address to use. Defaults to "127.0.0.1".
            client_port (int, optional): Defines the client port to use. Defaults to 30002.
            sr (int, optional): Defines the sampling rate for streaming audio. Defaults to 48000.
            buffer_size (int, optional): Defines the audio buffer size for streaming audio. Defaults to 256.
            bitres (int, optional): Defines the bit resolution for streaming audio. Defaults to 16.
            channels (int, optional): Defines the number of channels for streaming audio. Defaults to 2.
            set_device (bool, optional): Whether to choose a specific audio device (e.g. JACK if installed on your machine) or not. Defaults to False.
            verbose (bool, optional): Whether to print the latency measurements in real-time or not. Defaults to False.
        """

        self.server_ip = server_ip # socket.gethostbyname(socket.gethostname()) 
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port

        if set_device:
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

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, HEADER_SIZE + self.audio_buffer)
        self.UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, HEADER_SIZE + self.audio_buffer)
        self.UDPServerSocket.bind((self.server_ip, self.server_port))

        self.q = Queue()


    def listen(self):
        
        print('Waiting for connection...', (self.server_ip, (self.server_port)))

        stream = sd.RawOutputStream(samplerate=self.sr, blocksize=self.buffer_size, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
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
                stream.write(frame[12:]) 

            i = 1
        

    def send(self):

        # payload_size = self.audio_buffer - HEADER_SIZE
        # frame = b''.join([b'\x00'] * (payload_size))

        stream = sd.RawInputStream(samplerate=self.sr, blocksize=self.buffer_size, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()
        
        while True:
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

    server = Server(client_ip="127.0.0.1", sr=44100, buffer_size=512, channels=2, bitres=16, set_device=False, verbose=False)
    
    t1 = Thread(target=server.listen, args=())
    t2 = Thread(target=server.send, args=())
    t1.start()
    t2.start()