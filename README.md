# UDP Audio Stream Latency

This program uses the programming language Python for streaming audio and measuring Round-Trip Time (RTT) over UDP. This is based on three main Python libraries: 

- [socket](https://docs.python.org/3/library/socket.html#module-socket) to send messages across a network 
- [time](https://docs.python.org/3/library/time.html) to measure udp packet latency 
- [sounddevice](https://pypi.org/project/sounddevice/) for multiple channels of real-time streaming audio input and output

## Installation

Download [Anaconda](https://www.anaconda.com/products/distribution) and prepare your environment using the command line

```
conda create --name udp
conda activate udp
```
Install the required libraires

```
conda install -c anaconda pip
pip install sounddevice
``` 

## Usage

In order to connect to a peer, you first need to specify the IP addresses and ports of the server and the client in the python folder. 

```python
server_ip="0.0.0.0"
server_port=30001
client_ip="127.0.0.1"
client_port=30002
```
Moreover, you can set the audio stream parameters to use for streaming audio over the network.

```python
sr=48000 
buffer_size=256
bitres=16
channels=2
```

Finally, you can either measure UDP latency with real-time audio stream using your microphone and speakers (`stream=True`) or just by sending bytes packets equal to the size of the buffer required for the stream (`stream=False`)

**Server**
```
python server.py 
```
**Client**
```
python client.py 
```
