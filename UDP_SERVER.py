import socket
import time
from multiprocessing import Process, Queue

HEADER_SIZE = 4 + 8 # Packet index (4-bytes) and time (8-bytes)
JACKTRIP_HEADER = 16


class Server:

    def __init__(self, server_ip="0.0.0.0", server_port=30001, client_ip="127.0.0.1", client_port=30002):

        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind((self.server_ip, self.server_port))

    def listen(self, q, buffer_size=128, sr=48000, nchan=2, bit_resolution=16, verbose=True):

        if verbose:
            print(f'|  ---------- UDP Server Listening from Client {self.client_port} ------------  |')

        while True:
            packet, _ = self.UDPServerSocket.recvfrom(JACKTRIP_HEADER + int(bit_resolution / 8 * nchan * buffer_size))
            current_time = time.time_ns()
            packet_index = int.from_bytes(packet[:4], 'big')
            send_time = int.from_bytes(packet[4:12], 'big')
            q.put((packet_index, send_time - current_time))

            if packet_index == 0:
                break
      
    def send(self, q, buffer_size=128, sr=48000, nchan=2, bit_resolution=16, verbose=True):

        audio_buffer_size = (JACKTRIP_HEADER + int(bit_resolution / 8 * nchan * buffer_size)) # JackTrip audio buffer size
        _payload_size = audio_buffer_size - HEADER_SIZE
        _fill = b''.join([b'\x00'] * (_payload_size))

        while True:
            packet_index, time_diff = q.get()
            index_bytes = packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            time_bytes = (current_time + time_diff).to_bytes(8, 'big')

            packet = index_bytes + time_bytes + _fill
            self.UDPServerSocket.sendto(packet, (self.client_ip, self.client_port))

            if packet_index == 0:
                break
            if verbose:
                print(f'|  Server: {self.server_port}  |  Packet received and send back to Client: {packet_index}  |  Packet send back at time (ns): {current_time}  |')
    


if __name__ == "__main__":
    
    # SET AUDIO PARAMETERS
    buffer_size = 128
    sr = 48000
    nchan = 2
    bit_resolution = 16

    client_ip = "127.0.0.1"
    verbose = True

    server = Server(client_ip=client_ip)
    q = Queue()

    listen_process = Process(target=server.listen, args=(q, buffer_size, sr, nchan, bit_resolution, verbose))
    listen_process.start()
    server.send(q, buffer_size, sr, nchan, bit_resolution, verbose)
    listen_process.join()
    listen_process.close()