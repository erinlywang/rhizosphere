Skip to content
You said:
Hey I want to code the NIDAQmx in python such that it takes data continuously and plots that data
ChatGPT said:
To continuously acquire data from a NI DAQ (National Instruments Data Acquisition device) using NI-DAQmx and plot it in real time with Python, you’ll need the following:

✅ Requirements
NI-DAQmx driver installed on your system (from NI).

NI-DAQmx Python API: Install it using:

pip install nidaqmx
Matplotlib (for plotting):

pip install matplotlib
✅ Basic Structure of the Program
Here’s a simple example to continuously read analog input from a specified channel and plot it in real-time.

🔧 Example Code: Continuous Acquisition with Real-Time Plot
import nidaqmx
from nidaqmx.stream_readers import AnalogSingleChannelReader
from nidaqmx.constants import AcquisitionType
import matplotlib.pyplot as plt
import numpy as np
import threading
import time

# Settings
CHANNEL = "Dev1/ai0"         # Change this to your device and channel
SAMPLE_RATE = 1000           # Samples per second
SAMPLES_PER_READ = 100       # How many samples to read per loop

# Data buffer
data_buffer = np.zeros(SAMPLES_PER_READ)

# Plot setup
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot(data_buffer)
ax.set_ylim(-10, 10)  # Adjust based on expected input range

# Acquisition thread
def acquire_data():
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(CHANNEL)
        task.timing.cfg_samp_clk_timing(rate=SAMPLE_RATE,
                                        sample_mode=AcquisitionType.CONTINUOUS,
                                        samps_per_chan=SAMPLES_PER_READ)

        reader = AnalogSingleChannelReader(task.in_stream)
        task.start()

        while plt.fignum_exists(fig.number):
            reader.read_many_sample(data_buffer, number_of_samples_per_channel=SAMPLES_PER_READ, timeout=10.0)
            
            # Update plot
            line.set_ydata(data_buffer)
            line.set_xdata(np.arange(len(data_buffer)))
            ax.relim()
            ax.autoscale_view()
            plt.draw()
            plt.pause(0.01)

# Start acquisition in a background thread
thread = threading.Thread(target=acquire_data)
thread.daemon = True
thread.start()

# Keep the plot open
plt.show()
📌 Notes:
Replace "Dev1/ai0" with your actual device and channel name (check in NI MAX).

SAMPLE_RATE and SAMPLES_PER_READ can be tuned based on your application and system performance.

The plot updates in real time and will close when the plot window is closed.

🧪 Want to Add Features?
Let me know if you'd like to:

Save the data to a file

Plot multiple channels

Apply filtering or processing

Add GUI (e.g., with PyQt or Tkinter)

Triggered acquisition

Let me know how you want to extend it!

You said:
Could you also include the pylablib library and start and stop the data acquisition such that the data starts being collected when the piezo motor starts moving and stops taking data once the full range has been moved across (using the KIM101 piezo motor). 
ChatGPT said:
Here’s a more complete example script that uses pylablib to control a KIM101 piezo‑motor (via the Thorlabs/Kinesis interface) and uses nidaqmx to acquire data continuously from an NI DAQ. The acquisition starts when the motor begins moving and stops when the motor reaches the desired end position (full travel).

You will need to adapt it to your particular setup (channel names, device names, ranges, etc), but it gives the structure.

import time
import threading
import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.stream_readers import AnalogSingleChannelReader
from nidaqmx.constants import AcquisitionType

from pylablib.devices.Thorlabs.kinesis import KinesisPiezoMotor

# === Configuration ===
DAQ_CHANNEL = "Dev1/ai0"                   # analog input channel for NI DAQ
SAMPLE_RATE = 1000                         # samples per second
SAMPLES_PER_READ = 200                     # samples per read chunk

MOTOR_SERIAL = "12345678"                  # Serial number of the KIM101 controller
MOTOR_CHANNEL = 1                          # Which motor channel to use
MOTOR_MOVE_DISTANCE = 10.0                 # arbitrary units (e.g., µm) to move motor
MOTOR_END_POSITION = None                  # if you know absolute, you can use move_to

# === Global flags ===
_acquiring = False
_stop_requested = False

# === Function to run DAQ acquisition and plotting ===
def daq_acquire_plot():
    global _acquiring, _stop_requested

    # Initialize plot
    plt.ion()
    fig, ax = plt.subplots()
    data_buffer = np.zeros(SAMPLES_PER_READ)
    line, = ax.plot(data_buffer)
    ax.set_xlabel("Sample index")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Real‑time DAQ data")
    ax.set_ylim(-10, +10)  # set appropriately for your input range

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(DAQ_CHANNEL)
        task.timing.cfg_samp_clk_timing(rate=SAMPLE_RATE,
                                        sample_mode=AcquisitionType.CONTINUOUS,
                                        samps_per_chan=SAMPLES_PER_READ)
        reader = AnalogSingleChannelReader(task.in_stream)
        task.start()

        print("DAQ started")

        _acquiring = True
        try:
            while _acquiring and (not _stop_requested) and plt.fignum_exists(fig.number):
                reader.read_many_sample(data_buffer, number_of_samples_per_channel=SAMPLES_PER_READ, timeout=10.0)
                # update plot
                line.set_ydata(data_buffer)
                line.set_xdata(np.arange(len(data_buffer)))
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)
        finally:
            _acquiring = False
            print("DAQ stopped")

    plt.ioff()
    plt.show()

# === Main function controlling motor + acquisition ===
def run_experiment():
    global _stop_requested

    # Set up motor
    motor = KinesisPiezoMotor(MOTOR_SERIAL, default_channel=MOTOR_CHANNEL)
    motor.enable_channels(MOTOR_CHANNEL)
    print("Motor channel enabled")

    # Optionally, read current position
    start_position = motor.get_position(channel=MOTOR_CHANNEL)
    print(f"Start position: {start_position}")

    # Start the DAQ acquisition thread
    daq_thread = threading.Thread(target=daq_acquire_plot, daemon=True)
    daq_thread.start()

    # Wait until the DAQ thread has started acquiring
    while not _acquiring:
        time.sleep(0.01)

    # Now command the motor to move
    # Option A: move by a relative distance
    motor.move_by(MOTOR_MOVE_DISTANCE, channel=MOTOR_CHANNEL)
    print(f"Motor commanded to move by {MOTOR_MOVE_DISTANCE}")
    # Option B if you know the absolute end: motor.move_to(end_position, channel=MOTOR_CHANNEL)

    # Wait for motion to complete
    motor.wait_move(channel=MOTOR_CHANNEL)
    print("Motor move complete")

    # Once movement finishes, signal to stop acquisition
    _stop_requested = True

    # Optionally, join the thread
    daq_thread.join(timeout=5)
    print("Experiment finished")

if __name__ == "__main__":
    run_experiment()
📝 Explanation of how it works
The script uses pylablib.devices.Thorlabs.kinesis.KinesisPiezoMotor to interface with the KIM101 controller. 
pylablib.readthedocs.io
+2
pylablib.readthedocs.io
+2

It enables the motor channel, reads its starting position, then triggers a move.

In parallel, it starts a DAQ acquisition thread that continuously reads chunks of data and updates a real‑time plot.

The acquisition thread loops until _stop_requested becomes True (which we set right after the motor move completes).

Using a relative move_by ensures you move the motor across the “full range” you care about; you could also use move_to if you know the target end position.

The acquisition begins before the motor starts moving, and ends after the motor finishes moving, so you capture the full transit.

Plotting uses Matplotlib in interactive mode (plt.ion()), updating each chunk.

✅ What you’ll likely need to adapt
Adjust the DAQ channel name, input range, and plot Y‑limits based on your hardware and signal amplitude.

Ensure the sample rate (SAMPLE_RATE) and buffer size (SAMPLES_PER_READ) are appropriate for your data flow and system performance.

Set MOTOR_MOVE_DISTANCE (or target end position) to match the actual travel you want.

If you need to trigger the motor from software or detect the start of motion in another way, you could poll motor.is_moving() or use motor.get_status() to detect the motion start, rather than assuming the moment you call move_by is the start.

Consider error handling: e.g., handle motor errors, limit switches, DAQ read errors/timeouts, etc.

If you want the data acquisition only during the motor motion (i.e., start exactly when movement begins, stop exactly when it ends), you could refine the logic: start DAQ thread, then poll motor is_moving() until True, then when is_moving() becomes False stop the acquisition. For example:

motor.move_by(...)
while not motor.is_moving(channel=MOTOR_CHANNEL):
    time.sleep(0.001)
# we know motion has started
# ... then wait until it stops ...
motor.wait_move(channel=MOTOR_CHANNEL)
_stop_requested = True
