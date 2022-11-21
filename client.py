import socket, time, math, csv
from threading import Thread
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
                set_device=False, 
                verbose=False, 
                stream=False,
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
            set_device (bool, optional): Whether to choose a specific audio device (e.g. JACK if installed on your machine) or not. Defaults to False.
            verbose (bool, optional): Whether to print the latency measurements in real-time or not. Defaults to False.
            stream (bool, optional): Whether to stream audio using your microphone and speaker or not. Defaults to False.
            save_csv (bool, optional): Whether to save the udp latency measurements to a csv file or not. Defaults to False.
            running_time (int, optional): Defines the time (in seconds) needed for the measurements. Defaults to 10.
        """

        self.client_ip = client_ip # socket.gethostbyname(socket.gethostname())
        self.client_port = client_port
        self.server_ip = server_ip
        self.server_port = server_port

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
        self.running_time = running_time * 1e9  # convert to nanoseconds
        self.verbose = verbose
        self.stream = stream
        self.save_csv = save_csv
		
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPClientSocket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF, self.audio_buffer)
        self.UDPClientSocket.bind((self.client_ip, self.client_port))


    def listen(self):

        print('Waiting for connection...', (self.client_ip, (self.client_port)))

        latency, i = 0, 0

        stream = sd.RawOutputStream(samplerate=self.sr, blocksize=self.buffer_size, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
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
        

    def send(self):
        
        payload_size = self.audio_buffer - HEADER_SIZE
        frame = b''.join([b'\x00'] * (payload_size))

        stream = sd.RawInputStream(samplerate=self.sr, blocksize=self.buffer_size, device=self.device, channels=self.channels, dtype=f'int{str(self.bitres)}')
        stream.start()
  
        packet_index = 1
        packet_rate = self.sr / self.buffer_size
        total_packets = packet_rate * (self.running_time * 1e-9)
        period = 1 / packet_rate

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

            if not self.stream:
                time.sleep(period)            

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

    client = Client(server_ip="127.0.0.1", sr=44100, buffer_size=512, channels=2, bitres=16, set_device=False, stream=True, verbose=False, running_time=10)

    t1 = Thread(target=client.listen, args=())
    t2 = Thread(target=client.send, args=())
    t1.start()
    t2.start()