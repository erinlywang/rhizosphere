import time
import threading
import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.stream_readers import AnalogSingleChannelReader
from nidaqmx.constants import AcquisitionType
from pylablib.devices.Thorlabs.kinesis import KinesisPiezoMotor
from queue import Queue, Empty

# === Configuration ===
DAQ_CHANNEL = "Dev1/ai0"
SAMPLE_RATE = 1000
SAMPLES_PER_READ = 200

MOTOR_SERIAL = "12345678"    # Replace with your actual serial
MOTOR_CHANNEL = 1
MOTOR_MOVE_DISTANCE = 10.0

# === Shared variables ===
data_queue = Queue()
_stop_acquisition = threading.Event()

# === DAQ acquisition in background thread ===
def daq_acquire_thread():
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(DAQ_CHANNEL)
        task.timing.cfg_samp_clk_timing(rate=SAMPLE_RATE,
                                        sample_mode=AcquisitionType.CONTINUOUS,
                                        samps_per_chan=SAMPLES_PER_READ)

        reader = AnalogSingleChannelReader(task.in_stream)
        task.start()
        print("DAQ started")

        buffer = np.zeros(SAMPLES_PER_READ)

        try:
            while not _stop_acquisition.is_set():
                reader.read_many_sample(buffer, number_of_samples_per_channel=SAMPLES_PER_READ, timeout=10.0)
                data_queue.put(buffer.copy())
        finally:
            print("DAQ stopped")

# === Main experiment logic ===
def run_experiment():
    global data_queue

    # Motor setup
    motor = KinesisPiezoMotor(MOTOR_SERIAL, default_channel=MOTOR_CHANNEL)
    motor.enable_channels(MOTOR_CHANNEL)
    print("Motor channel enabled")

    # Start DAQ thread
    daq_thread = threading.Thread(target=daq_acquire_thread, daemon=True)
    daq_thread.start()

    # Wait briefly to start data collection before moving
    time.sleep(0.5)

    # Start motor move
    motor.move_by(MOTOR_MOVE_DISTANCE, channel=MOTOR_CHANNEL)
    print(f"Motor commanded to move by {MOTOR_MOVE_DISTANCE}")
    motor.wait_move(channel=MOTOR_CHANNEL)
    print("Motor move complete")

    # Signal to stop DAQ and wait for thread to finish
    _stop_acquisition.set()
    daq_thread.join()

    print("Experiment finished")

# === Plotting in the main thread ===
def live_plot():
    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.plot([], [])
    ax.set_ylim(-10, 10)
    ax.set_xlim(0, SAMPLES_PER_READ)
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("Voltage")

    buffer = np.zeros(SAMPLES_PER_READ)

    while not _stop_acquisition.is_set() or not data_queue.empty():
        try:
            data = data_queue.get(timeout=0.1)
            line.set_ydata(data)
            line.set_xdata(np.arange(len(data)))
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw()
            fig.canvas.flush_events()
        except Empty:
            continue

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    # Start plotting in main thread
    plot_thread = threading.Thread(target=live_plot)
    plot_thread.start()

    # Run motor and DAQ logic in main thread
    run_experiment()

    # Wait for plot to finish
    plot_thread.join()
