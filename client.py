import socket
import time, math, csv
from threading import Thread
from multiprocessing import Queue
import sounddevice as sd


results = []
HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)

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
                stream=False, 
                running_time=10):

        self.client_ip = client_ip # socket.gethostbyname(socket.gethostname())
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port

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
        self.running_time = running_time * 1e9  # convert to nanoseconds
        self.verbose = verbose
        self.stream = stream
		
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPClientSocket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF, self.audio_buffer)
        self.UDPClientSocket.bind((self.client_ip, self.client_port))

        self.q = Queue()

    def listen(self):

        print('Waiting for connection...', (self.client_ip, (self.client_port)))

        def record():

            latency, i = 0, 0

            stream = sd.RawOutputStream(samplerate=self.sr, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
            stream.start()

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
                    if self.stream:
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

        t1 = Thread(target=record, args=())
        t1.start()
        

    def send(self):
        
        packet_index = 1

        payload_size = self.audio_buffer - HEADER_SIZE
        frame = b''.join([b'\x00'] * (payload_size))

        packet_rate = self.sr / self.buffer_size
        total_packets = packet_rate * (self.running_time * 1e-9)

        stream = sd.RawInputStream(samplerate=self.sr, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()

        start_time = time.time_ns()
        
        while True:

            if self.stream:
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
        var = sum(pow(x - latency_avg, 2) for x in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = max(latency_list) - min(latency_list)
        cycle = (results[-1][3] - results[0][3]) * 1e-9
        bandwidth = sum([x[4] for x in results]) / cycle
        packet_loss = (max([x[0] for x in results]) - len(latency_list)) 

        print('\n| ---------------  Summary  ----------------- |\n')
        print('Total %d packets are received in %f seconds' % (len(results), cycle))
        print('Average RTT latency: %f second' % latency_avg)
        print('Maximum RTT latency: %f second' % latency_max)
        print('Std RTT latency: %f second' % latency_std)
        print('Effective bandwidth: %f Mbps' % ((self.sr / self.buffer_size) * bandwidth * 8 / 1024 / 1024))
        print('Jitter: %f second' % jitter)
        print('Packet loss: %d' % int(packet_loss))

        with open(f'results_{self.sr}_{self.buffer_size}_{self.channels}.csv', 'w') as f:
            writer = csv.writer(f, delimiter=',')
            content = [['packet-index', 'latency', 'jitter', 'received-time', 'packet-size', 'packet-rate']]
            writer.writerows(content + results)

        return {'Latency (avg)': latency_avg, 'Latency (max)': latency_max, 'Jitter': jitter, 'Bandwidth': bandwidth}


if __name__ == "__main__":

    client = Client(server_ip="127.0.0.1", sr=44100, buffer_size=512, channels=2, bitres=32, device=False, stream=True, verbose=False, running_time=10)

    t1 = Thread(target=client.listen, args=())
    t2 = Thread(target=client.send, args=())
    t1.start()
    t2.start()