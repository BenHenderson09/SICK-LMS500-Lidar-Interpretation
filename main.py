import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import math

PORT = "COM7"
BAUD = 57600

def parse_lmdscandata(telegram: str):
    tokens = telegram.strip().split(" ")

    if len(tokens) < 30:
        raise ValueError("Telegram too short")

    header = tokens[:18]
    cmd_type = header[0]
    cmd_name = header[1]

    if cmd_name != "LMDscandata" or cmd_type not in ("sRA", "sSN"):
        raise ValueError("Not an LMDscandata telegram")

    sections = tokens[18:]
    if len(sections) < 8:
        raise ValueError("Sections too short")

    enc_blocks = int(sections[0], 10)
    if enc_blocks != 0:
        raise ValueError("Unexpected encoder block count")

    chan16_blocks = int(sections[1], 10)
    if chan16_blocks < 1:
        raise ValueError("No 16-bit channel blocks")

    if sections[2] != "DIST1":
        raise ValueError("Expected DIST1 channel")

    scale_hex = sections[3]
    if scale_hex not in ("3F800000", "40000000"):
        raise ValueError("Unexpected scale factor")
    scale_factor = 1 if scale_hex == "3F800000" else 2

    start_angle_1e4 = int(sections[5], 16)
    angle_step_1e4 = int(sections[6], 16)
    value_count = int(sections[7], 16)

    if len(sections) < 8 + value_count:
        raise ValueError("Not enough values")

    vals = sections[8 : 8 + value_count]
    distances_mm = [int(v, 16) * scale_factor for v in vals]

    start_deg = start_angle_1e4 / 10000.0
    step_deg = angle_step_1e4 / 10000.0
    angles_deg = [start_deg + i * step_deg for i in range(value_count)]

    return distances_mm, angles_deg


def polar_to_cartesian(dist_mm, angles_deg):
    r = np.array(dist_mm) / 1000.0
    theta = np.deg2rad(np.array(angles_deg))
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y


def apply_rotation(x, y, deg):
    phi = np.deg2rad(deg)
    cos_p = np.cos(phi)
    sin_p = np.sin(phi)
    xr = x * cos_p - y * sin_p
    yr = x * sin_p + y * cos_p
    return xr, yr



def main():
    ser = serial.Serial(
        PORT, BAUD,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.1,
    )
    print(f"Opened {PORT} @ {BAUD}")

    ser.write(b"\x02sEN LMDscandata 1\x03")
    ser.flush()

    buffer = b""

    # Plot and slider
    plt.ion()
    fig, ax = plt.subplots()

    plt.subplots_adjust(bottom=0.25)

    scatter = ax.scatter([], [], s=3)
    ax.scatter([0], [0], marker="s", s=50, color="blue", zorder=5)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("SICK LMS500 Point Cloud (Rotation Adjustable)")
    ax.grid(True)

    # FIXED AXES
    ax.set_xlim(-6, 6)
    ax.set_ylim(-1, 6)

    ax.set_xticks(np.arange(-6, 7, 1))
    ax.set_yticks(np.arange(-1, 7, 1))

    # Coordinate readings
    coord_text = ax.text(
        0.02, 0.98, "",
        transform=ax.transAxes,
        va="top", ha="left"
    )

    # Rotation slider
    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.05])
    rot_slider = Slider(
        ax=ax_slider,
        label="Rotation (deg)",
        valmin=-45,
        valmax=45,
        valinit=-18,    # default offset
        valstep=0.1
    )

    last_x = None
    last_y = None

    def update_rotation(val):
        nonlocal last_x, last_y
        if last_x is None:
            return
        xr, yr = apply_rotation(last_x, last_y, rot_slider.val)
        scatter.set_offsets(np.c_[xr, yr])
        fig.canvas.draw_idle()

    rot_slider.on_changed(update_rotation)

    def on_move(event):
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            coord_text.set_text("")
        else:
            coord_text.set_text(f"x = {event.xdata:.2f} m, y = {event.ydata:.2f} m, hypot = {math.sqrt(math.pow(event.ydata, 2) + math.pow(event.xdata, 2)):.2f}")
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)

    # Main loop
    try:
        while True:
            chunk = ser.read(4096)
            if chunk:
                buffer += chunk

            while b"\x02" in buffer and b"\x03" in buffer:
                s_idx = buffer.find(b"\x02")
                e_idx = buffer.find(b"\x03", s_idx)
                if e_idx == -1:
                    break

                telegram = buffer[s_idx+1:e_idx]
                buffer = buffer[e_idx+1:]

                try:
                    s = telegram.decode(errors="replace")
                    dist_mm, ang_deg = parse_lmdscandata(s)

                    x, y = polar_to_cartesian(dist_mm, ang_deg)

                    last_x, last_y = x, y
                    xr, yr = apply_rotation(x, y, rot_slider.val)

                    scatter.set_offsets(np.c_[xr, yr])
                    fig.canvas.draw()
                    fig.canvas.flush_events()

                except ValueError:
                    pass

    except KeyboardInterrupt:
        print("Stopping...")
        try:
            ser.write(b"\x02sEN LMDscandata 0\x03")
            ser.flush()
        except Exception:
            pass

    finally:
        ser.close()
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
