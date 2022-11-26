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
| --ip     | Defines the remote IP address to connect to.                                                                           | "127.0.0.1"   |
| --sr     | Defines the sampling rate for streaming audio.                                                                  | 48000         |
| -b       | Defines the audio buffer size for streaming audio.                                                              | 256           |
| --bit    | Defines the bit resolution for streaming audio.                                                                 | 16            |
| --ch     | Defines the number of channels for streaming audio.                                                             | 1             |
| --sp     | Defines the server port to use.                                                                                 | 30001         |
| --cp     | Defines the client port to use.                                                                                 | 30002         |
| -d       | Whether to choose specific input/output devices or not (e.g. [1,3]). If set to True shows the device available. | None          |
| -v       | Whether to print the latency measurements in real-time or not.                                                  | False         |
| --save   | Whether to save the udp latency measurements to a csv file or not.                                              | True          |
| -t       | Defines the time (in seconds) needed for the measurements.                                                      | 10            |

## Checking Available Hardware

[sounddevice](https://pypi.org/project/sounddevice/) makes it possible to list each available device on one line together with the corresponding device ID, which can be assigned to stream audio. In order to display the list of available device set the argument `-d` to `True`. 

**Example**
```
  0 Built-in Line Input, Core Audio (2 in, 0 out)
> 1 Built-in Digital Input, Core Audio (2 in, 0 out)
< 2 Built-in Output, Core Audio (0 in, 2 out)
  3 Built-in Line Output, Core Audio (0 in, 2 out)
  4 Built-in Digital Output, Core Audio (0 in, 2 out)

Select input/output device index (e.g. 1, 3):
```

The first character of a line is `>` for the default input device, `<` for the default output device and `*` for the default input/output device. After the device ID and the device name, the corresponding host API name is displayed. In the end of each line, the maximum number of input and output channels is shown. More information [here](https://python-sounddevice.readthedocs.io/en/0.3.15/api/checking-hardware.html#sounddevice.query_devices).

Finally, you can also specify input/output devices directly in the command-line using the `-d` argument and a list `[1, 3]`. Default parameter will use default input/output device.

