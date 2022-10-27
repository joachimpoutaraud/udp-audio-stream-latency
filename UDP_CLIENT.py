import socket
import time
from multiprocessing import Process, Queue
import math
import csv

HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)
JACKTRIP_HEADER = 16


class Client:

    def __init__(self, client_ip="0.0.0.0", client_port=30002, server_ip="127.0.0.1", server_port=30001):

        self.client_ip = client_ip
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port
        self.send_log = []
        self.receive_log = []
        self.packet_index = 1

        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPClientSocket.bind((self.client_ip, self.client_port))

    def send(self, running_time, q, buffer_size=128, sr=48000, nchan=2, bit_resolution=16, verbose=True):

        audio_buffer_size = (JACKTRIP_HEADER + int(bit_resolution / 8 * nchan * buffer_size)) # JackTrip audio buffer size
        _payload_size = audio_buffer_size - HEADER_SIZE
        _fill = b''.join([b'\x00'] * (_payload_size))
        
        packet_rate = sr / buffer_size
        total_packets = running_time * packet_rate
        running_time = running_time * 1e9 # convert to nanoseconds
        period = 1 / packet_rate

        start_time = time.time_ns()

        while True:
            index_bytes = self.packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            packet = index_bytes + current_time.to_bytes(8, 'big') + _fill
            send_nums = self.UDPClientSocket.sendto(packet, (self.server_ip, self.server_port))
            self.send_log.append([self.packet_index, current_time, send_nums])

            if (current_time - start_time) > running_time or self.packet_index >= total_packets:
                break

            self.packet_index += 1
            time.sleep(period)

        while q.empty():
            self.UDPClientSocket.sendto((0).to_bytes(4, 'big'), (self.server_ip, self.server_port))
            time.sleep(0.05)
        self.UDPClientSocket.close()

    def listen(self, q, buffer_size=128, sr=48000, nchan=2, bit_resolution=16, verbose=True, save=False):

        latency = 0

        while True:
            packet, addr = self.UDPClientSocket.recvfrom(JACKTRIP_HEADER + int(bit_resolution / 8 * nchan * buffer_size))
            received_time = time.time_ns()
            packet_index = int.from_bytes(packet[:4], 'big')
            send_time = int.from_bytes(packet[4:12], 'big')

            if packet_index == 0:
                break
            else:
                old_latency = latency
                latency = round(((received_time - send_time) * 1e-9) / 2, 6) # convert to seconds
                jitter = abs(latency - old_latency)
                packet_size = len(packet)

                self.receive_log.append([packet_index, latency, jitter, received_time, packet_size])

                if verbose:
                    print(f'|  Server: {self.server_port}  |  Packet index: {packet_index}  |  Latency (s): {latency} ｜ Jitter: {jitter}  |  Packet size: {packet_size}  |')

        self.evaluate()

        if self.save_csv:
            self.save_csv(f'results{buffer_size}_{sr}_{nchan}_{bit_resolution}.csv')
        q.put(0)

    def evaluate(self):
        latency_list = [row[1] for row in self.receive_log]
        latency_max = max(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(x - latency_avg, 2) for x in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = max(latency_list) - min(latency_list)
        cycle = (self.receive_log[-1][3] - self.receive_log[0][3]) * 1e-9
        bandwidth = sum([x[4] for x in self.receive_log]) / cycle
        packet_loss = (max([x[0] for x in self.receive_log]) - len(latency_list)) / max([x[0] for x in self.receive_log])

        print('\n| -------------  Summary  --------------- |\n')
        print('Total %d packets are received in %f seconds' % (len(self.receive_log), cycle))
        print('Average RTT latency: %f second' % latency_avg)
        print('Maximum RTT latency: %f second' % latency_max)
        print('Std RTT latency: %f second' % latency_std)
        print('bandwidth: %f Mbits' % (bandwidth * 8 / 1024 / 1024))
        print('Jitter (Latency Max - Min): %f second' % jitter)
        print('Packet loss: %f' % packet_loss)

        return {'latency_max': latency_max, 'latency_avg': latency_avg, 'jitter': jitter, 'bandwidth': bandwidth}

    def save_csv(self, path):

        with open(path, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            content = [['packet-index', 'latency', 'jitter', 'received-time', 'packet-size', 'packet-rate']]
            writer.writerows(content + self.receive_log)



if __name__ == "__main__":

    running_time = 10 # seconds
    
    # SET AUDIO PARAMETERS
    buffer_size = 128
    sr = 48000
    nchan = 2
    bit_resolution = 16

    server_ip = "127.0.0.1"
    save_csv = True
    verbose = True
    
    # UDP CLIENT
    client = Client(server_ip=server_ip)
    q = Queue()

    listen_process = Process(target=client.listen, args=(q, buffer_size, sr, nchan, bit_resolution, verbose, save_csv))
    listen_process.start()
    client.send(running_time, q, buffer_size, sr, nchan, bit_resolution, verbose)
    listen_process.join()
    listen_process.close()