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
