import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import matplotlib.pyplot as plt

plt.ylim((0, 2))
plt.ion()

i = 0
with nidaqmx.Task() as task:
  task.ai_channels.add_ai_voltage_chan("Dev1/ai1", terminal_config= TerminalConfiguration.NRSE)
  while i<100:
    data = task.read(number_of_samples_per_channel=1)
    plt.scatter(i, data[0], c='r')
    plt.pause(0.05)

    i = i + 1
