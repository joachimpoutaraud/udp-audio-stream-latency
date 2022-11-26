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

In order to establish a peer-to-peer connection, you can specify the following arguments in the command-line. 

**Server**
```python
python udpstream.py -s --ip <client ip> --sr <sampling rate> -b <buffer size> --bit <bit resolution> --ch <channels> --sp <server port> --cp <client port> -d <bool or list> -v <bool>
```
**Client**
```python
python udpstream.py -c --ip <server ip> --sr <sampling rate> -b <buffer size> --bit <bit resolution> --ch <channels> --sp <server port> --cp <client port> -d <bool or list> -v <bool> --save <save csv> -t <running time>
```

## Arguments

| Argument | Description                                                                                                     | Default Value |
|----------|-----------------------------------------------------------------------------------------------------------------|---------------|
| -s       | Server                                                                                                          | N/A           |
| -c       | Client                                                                                                          | N/A           |
| --ip     | Defines the IP Address to connect to.                                                                           | "127.0.0.1"   |
| --sr     | Defines the sampling rate for streaming audio.                                                                  | 48000         |
| -b       | Defines the audio buffer size for streaming audio.                                                              | 256           |
| --bit    | Defines the bit resolution for streaming audio.                                                                 | 16            |
| --ch     | Defines the number of channels for streaming audio.                                                             | 1             |
| --sp     | Defines the server port to use.                                                                                 | 30001         |
| --cp     | Defines the client port to use.                                                                                 | 30002         |
| -d       | Whether to choose specific input/output devices or not (e.g. [1,3]). If set to True shows the device available. | None          |
| -v       | Whether to print the latency measurements in real-time or not.                                                  | False         |
| --save   | Whether to save the udp latency measurements to a csv file or not.                                              | True         |
| -t       | Defines the time (in seconds) needed for the measurements.                                                      | 10            |

