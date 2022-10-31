import socket
import pyaudio, time, math, csv
from threading import Thread
from multiprocessing import Process, Queue


HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)
results = []

class Client:

    def __init__(self, client_port=30002, server_ip="127.0.0.1", server_port=30001, sr=48000, buffer_size=1024, bitres=16, channels=2, running_time=10, verbose=False):

        self.client_ip = "0.0.0.0" # socket.gethostbyname(socket.gethostname())
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port
        
        self.sr = sr
        self.buffer_size = buffer_size
        self.audio_buffer = int((bitres / 8) * channels * buffer_size)
        self.channels = channels
        self.running_time = running_time * 1e9  # convert to nanoseconds
        self.verbose = verbose
		
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

        def record(audio_buffer, period):

            latency, i = 0, 0

            start_time = time.time_ns()
            while True:
                frame, server_addr = self.UDPClientSocket.recvfrom(HEADER_SIZE + audio_buffer)

                received_time = time.time_ns()
                packet_index = int.from_bytes(frame[:4], 'big')
                send_time = int.from_bytes(frame[4:12], 'big')

                if i == 0:
                    print('Connection from Peer!', server_addr)
                if (received_time - start_time) > self.running_time:
                    break
                else:
                    self.record.write(frame[12:])
                    time.sleep(period)

                    old_latency = latency
                    latency = round(((received_time - send_time) * 1e-9) / 2, 6) # convert to seconds
                    jitter = abs(latency - old_latency)
                    packet_size = len(frame)

                    results.append([packet_index, latency, jitter, received_time, packet_size])

                    if self.verbose:
                        print(f'|  Packet index: {packet_index}  |  Latency (s): {latency} ｜ Jitter (s): {jitter}  |  Packet size (bytes): {packet_size}  |')
                i = 1

            self.evaluate()

        t1 = Thread(target=record, args=(self.audio_buffer, period))
        t1.start()
        

    def send(self):

        packet_rate = self.sr / self.buffer_size
        period = 1 / packet_rate

        def play(buffer_size, period):

            packet_index = 1

            while True:
                frame = self.play.read(buffer_size, exception_on_overflow=False) # Ignore overflow IOError

                index_bytes = packet_index.to_bytes(4, 'big')
                current_time = time.time_ns()
                time_bytes = current_time.to_bytes(8, 'big')
                frame = index_bytes + time_bytes + frame

                self.UDPClientSocket.sendto(frame, (self.server_ip, self.server_port))

                time.sleep(period)  
                packet_index += 1

        t1 = Thread(target=play, args=(self.buffer_size, period))
        t1.start()  


    def evaluate(self, save=True):

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
        print('bandwidth: %f Mbits' % (bandwidth * 8 / 1024 / 1024))
        print('Jitter (Latency Max - Min): %f second' % jitter)
        print('Packet loss: %d' % int(packet_loss))

        if save:
            with open(f'results_{self.sr}_{self.buffer_size}_{self.channels}.csv', 'w') as f:
                writer = csv.writer(f, delimiter=',')
                content = [['packet-index', 'latency', 'jitter', 'received-time', 'packet-size', 'packet-rate']]
                writer.writerows(content + results)

        return {'latency_max': latency_max, 'latency_avg': latency_avg, 'jitter': jitter, 'bandwidth': bandwidth}


if __name__ == "__main__":

    client = Client(server_ip="127.0.0.1", sr=48000, buffer_size=1024, channels=2, running_time=5, verbose=False)

    t1 = Thread(target=client.listen, args=())
    t2 = Thread(target=client.send, args=())
    t1.start()
    t2.start()