import socket, time, sys, getopt, math, csv
from threading import Thread
from multiprocessing import Queue
import sounddevice as sd

results = []
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
            device (bool, optional): Whether to choose specific input/output devices or not (e.g. [1,3]). If set to True shows the device available. Defaults to None.
            verbose (bool, optional): Whether to print the latency measurements in each iteration or not. Defaults to False.
        """

        self.server_ip = server_ip # socket.gethostbyname(socket.gethostname()) 
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port

        if device == True:
            print(sd.query_devices())
            devicein, deviceout = input("\nSelect input/output device index (e.g. 1, 3): ").split(",")
            sd.default.device = [int(devicein), int(deviceout)]
        else:
            sd.default.device = device
        
        self.sr = sr
        self.buffer_size = buffer_size
        self.bitres = bitres
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels
        self.verbose = verbose

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # self.UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, HEADER_SIZE + self.audio_buffer)
        # self.UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, HEADER_SIZE + self.audio_buffer)
        self.UDPServerSocket.bind((self.server_ip, self.server_port))

        self.q = Queue()


    def listen(self):
        
        print('Waiting for connection...', (self.server_ip, (self.server_port)))

        stream = sd.RawOutputStream(samplerate=self.sr, blocksize=self.buffer_size, channels=self.channels, dtype=f'int{str(self.bitres)}')
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

        stream = sd.RawInputStream(samplerate=self.sr, blocksize=self.buffer_size, channels=self.channels, dtype=f'int{str(self.bitres)}')
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

class Client:

    def __init__(self, 
                client_ip="0.0.0.0",
                client_port=30002, 
                server_ip="127.0.0.1", 
                server_port=30001, 
                sr=48000, 
                buffer_size=256, 
                bitres=16, 
                channels=2,
                device=None, 
                verbose=False, 
                save_csv=False, 
                running_time=10):
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
            client_ip (str, optional): Defines the client IP address to use. Defaults to "0.0.0.0".
            client_port (int, optional): Defines the client port to use. Defaults to 30002.
            server_ip (str, optional): Defines the server IP address to use. Defaults to "127.0.0.1".
            server_port (int, optional): Defines the server port to use. Defaults to 30001.
            sr (int, optional): Defines the sampling rate for streaming audio. Defaults to 48000.
            buffer_size (int, optional): Defines the audio buffer size for streaming audio. Defaults to 256.
            bitres (int, optional): Defines the bit resolution for streaming audio. Defaults to 16.
            channels (int, optional): Defines the number of channels for streaming audio. Defaults to 2.
            device (bool, optional): Whether to choose specific input/output device or not (e.g. [1,3]). If set to True shows the devices available. Defaults to None.
            verbose (bool, optional): Whether to print the latency measurements in each iteration or not. Defaults to False.
            save_csv (bool, optional): Whether to save the udp latency measurements to a csv file or not. Defaults to False.
            running_time (int, optional): Defines the time (in seconds) needed for the measurements. Defaults to 10.
        """

        self.client_ip = client_ip # socket.gethostbyname(socket.gethostname())
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port

        if device == True:
            print(sd.query_devices())
            devicein, deviceout = input("\nSelect input/output device index (e.g. 1, 3): ").split(",")
            sd.default.device = [int(devicein), int(deviceout)]
        else:
            sd.default.device = device

        self.sr = sr
        self.buffer_size = buffer_size
        self.bitres = bitres
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels
        self.running_time = running_time * 1e9  # convert to nanoseconds
        self.verbose = verbose
        self.save_csv = save_csv
		
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # self.UDPClientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, HEADER_SIZE + self.audio_buffer)
        # self.UDPClientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, HEADER_SIZE + self.audio_buffer)
        self.UDPClientSocket.bind((self.client_ip, self.client_port))
        

    def listen(self):

        print('Waiting for connection...', (self.client_ip, (self.client_port)))

        stream = sd.RawOutputStream(samplerate=self.sr, blocksize=self.buffer_size, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()

        latency, i = 0, 0

        while True:
            frame, server_addr = self.UDPClientSocket.recvfrom(HEADER_SIZE + self.audio_buffer)

            received_time = time.time_ns()
            packet_index = int.from_bytes(frame[:4], 'big')
            send_time = int.from_bytes(frame[4:12], 'big')

            if i == 0:
                print('Connection from Peer!', server_addr)
            if packet_index == 0:
                break
            else:
                stream.write(frame[12:])

                old_latency = latency
                latency = round(((received_time - send_time) * 1e-9) / 2, 6) # convert to seconds
                jitter = abs(latency - old_latency)
                packet_size = len(frame)

                results.append([packet_index, latency, jitter, received_time, packet_size])

                if self.verbose:
                    print(f'|  Packet index: {packet_index}  |  Latency (s): {latency} ｜ Jitter (s): {jitter}  |  Packet size (bytes): {packet_size}  |')
            i = 1

        self.evaluate()
        

    def send(self):
        
        # payload_size = self.audio_buffer - HEADER_SIZE
        # frame = b''.join([b'\x00'] * (payload_size))

        stream = sd.RawInputStream(samplerate=self.sr, blocksize=self.buffer_size, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()
  
        packet_index = 1
        packet_rate = self.sr / self.buffer_size
        total_packets = packet_rate * (self.running_time * 1e-9)

        start_time = time.time_ns()
        
        while True:
            frame = stream.read(self.buffer_size)[0]               

            index_bytes = packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            time_bytes = current_time.to_bytes(8, 'big')
            packet = index_bytes + time_bytes + frame

            if (current_time - start_time) > self.running_time or packet_index >= total_packets:
                break

            self.UDPClientSocket.sendto(packet, (self.server_ip, self.server_port))
            packet_index += 1             

        packet_index = (0).to_bytes(4, 'big') 
        self.UDPClientSocket.sendto(packet_index, (self.server_ip, self.server_port)) 


    def evaluate(self):

        latency_list = [row[1] for row in results]
        latency_max = max(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(row - latency_avg, 2) for row in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = max(latency_list) - min(latency_list)
        cycle = (results[-1][3] - results[0][3]) * 1e-9
        bandwidth = sum([row[4] for row in results]) / cycle
        packet_loss = (max([row[0] for row in results]) - len(latency_list)) 

        print('\n| ---------------  Summary  ----------------- |\n')
        print('Total %d packets are received in %f seconds' % (len(results), cycle))
        print('Average RTT latency: %f second' % latency_avg)
        print('Maximum RTT latency: %f second' % latency_max)
        print('Std RTT latency: %f second' % latency_std)
        print('Effective bandwidth: %f Mbps' % ((self.sr / self.buffer_size) * bandwidth * 8 / 1024 / 1024))
        print('Jitter: %f second' % jitter)
        print('Packet loss: %d' % int(packet_loss))

        if self.save_csv:
            with open(f'results_{self.sr}_{self.buffer_size}_{self.channels}.csv', 'w') as f:
                writer = csv.writer(f, delimiter=',')
                content = [['packet-index', 'latency', 'jitter', 'received-time', 'packet-size', 'packet-rate']]
                writer.writerows(content + results)

        return {'Latency (avg)': latency_avg, 'Latency (max)': latency_max, 'Jitter': jitter, 'Bandwidth': bandwidth}  
             
if __name__ == "__main__":

    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csf:b:v:d:t:', ["ip=", "sr=", "buffer=", "bit=", "ch=", "sp=", "cp=", "device=", "verbose=", "save="])

        opts = dict(opts)
        opts.setdefault('--ip', "127.0.0.1")
        opts.setdefault('--sr', "48000")
        opts.setdefault('-b', "256")
        opts.setdefault('--bit', "16")
        opts.setdefault('--ch', "1")
        opts.setdefault('--sp', "30001")
        opts.setdefault('--cp', "30002")
        opts.setdefault('-d', "None")
        opts.setdefault('-v', "False")
        opts.setdefault('--save', "False")
        opts.setdefault('-t', "10")
    
    except getopt.GetoptError:
        print('Server: udpstream.py -s --ip <client ip> --sr <sampling rate> -b <buffer size> --bit <bit resolution> --ch <channels> --sp <server port> --cp <client port> -d <bool or list> -v <bool>')
        print('Client: udpstream.py -c --ip <server ip> --sr <sampling rate> -b <buffer size> --bit <bit resolution> --ch <channels> --sp <server port> --cp <client port> -d <bool or list> -v <bool> --save <save csv> -t <running time>')
        sys.exit(2)

    if '-s' in opts.keys():

        server = Server(client_ip=opts['--ip'], sr=int(opts['--sr']), buffer_size=int(opts['-b']), bitres=int(opts['--bit']), channels=int(opts['--ch']), 
        server_port=int(opts['--sp']), client_port=int(opts['--cp']), device=eval(opts['-d']), verbose=eval(opts['-v']))

        t1 = Thread(target=server.listen, args=())
        t2 = Thread(target=server.send, args=())
        t1.start()
        t2.start()

    if '-c' in opts.keys():

        client = Client(server_ip=opts['--ip'], sr=int(opts['--sr']), buffer_size=int(opts['-b']), bitres=int(opts['--bit']), channels=int(opts['--ch']), 
        client_port=int(opts['--cp']), server_port=int(opts['--sp']), device=eval(opts['-d']), verbose=eval(opts['-v']), save_csv=eval(opts['--save']), running_time=int(opts['-t']))

        t1 = Thread(target=client.listen, args=())
        t2 = Thread(target=client.send, args=())
        t1.start()
        t2.start()

