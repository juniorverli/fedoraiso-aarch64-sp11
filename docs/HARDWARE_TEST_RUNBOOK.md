# Surface Pro 11 LCD hardware validation

Target: Snapdragon X Plus X1P64100 Surface Pro 11 LCD. Image: Fedora Workstation 44 AArch64 GNOME Wayland remix, `output/fedora-44-workstation-surface-pro-11-lcd.iso`. Static integration reports in `output/workstation44-evidence/` verify included artifacts. Every hardware result below remains unverified until observed on the tablet.

## Prepare and boot

Verify the locally generated checksum before writing the ISO:

```bash
cd output
sha256sum -c fedora-44-workstation-surface-pro-11-lcd.iso.sha256
```

Write the ISO to a USB drive of at least 8 GB using GNOME Disks or Fedora Media Writer. Select the correct removable device; writing replaces its contents. Preserve the existing internal installation for live testing.

Enter Surface UEFI by holding Volume Up while pressing Power. Disable Secure Boot for the unsigned custom GRUB/kernel, then enable USB boot. Start with the GRUB entry **Fedora Workstation 44 Live (Surface Pro 11 LCD / GNOME Wayland)**. Record whether GRUB, kernel text, initramfs and GNOME each appear. The official live user and installer should be available; do not assume the legacy `surface:surface` account exists.

If the display goes black, reboot into **Fedora Workstation 44 diagnostics (firmware display / no GPU modesetting)**. This entry uses `earlycon=efifb keep_bootcon`, prevents MSM modesetting and requests a text session. Record the last visible line or photograph it. A successful diagnostic boot does not establish that accelerated graphics work. If dracut offers a shell, collect `/run/initramfs/rdsosreport.txt` and `dmesg`, along with `lsblk -f`, `cat /proc/cmdline` and `lsmod`.

## Save evidence

Connect a separate writable device and select its actual mount location. Copy logs locally; they may contain device identifiers, network information and proprietary firmware references. Do not publish firmware blobs.

```bash
mkdir -p "$HOME/surface-validation"
cat /etc/os-release > "$HOME/surface-validation/os-release.txt"
uname -a > "$HOME/surface-validation/kernel.txt"
cat /proc/cmdline > "$HOME/surface-validation/cmdline.txt"
sudo journalctl -b > "$HOME/surface-validation/journal.txt"
sudo dmesg > "$HOME/surface-validation/dmesg.txt"
lsblk -f > "$HOME/surface-validation/storage.txt"
loginctl show-session "$XDG_SESSION_ID" -p Type > "$HOME/surface-validation/session.txt"
```

Record ISO SHA256, boot entry, observed result and relevant log lines for each test. Expected behavior below is an acceptance target, not an established result. Diagnostic utilities may require installation into the temporary live session.

## Subsystem checks

| Area | Procedure | Acceptance target |
|---|---|---|
| Base and live session | Inspect `/etc/os-release`, `uname -r`, session type and launch the installer without starting disk changes. | Fedora 44 Workstation, matching Surface kernel, GNOME Wayland, Anaconda opens. |
| USB live root | `lsblk -f`; inspect `journalctl -b -k` for xHCI, UAS, USB storage and live-root errors. Test a second USB storage device. | Live root is found, external device reads correctly and no disconnect loop occurs. |
| LCD and brightness | Inspect `/sys/class/drm/*eDP*/status`, `*/modes` and `/sys/class/backlight/`; adjust brightness through GNOME Settings. | 2880×1920 panel visible, brightness responds, GNOME exposes supported refresh rates. Test 120 Hz explicitly. |
| GPU | Run `glxinfo -B` and `vulkaninfo --summary` if installed; inspect DRM errors. | Freedreno/Turnip renderer and stable accelerated desktop. Record actual renderer and version. |
| Keyboard/touchpad | `sudo libinput list-devices` and `sudo libinput debug-events`; type, scroll, gesture, detach and reattach. | Input and tablet posture events work. Test Flex Keyboard Bluetooth mode separately. |
| Touch and pen | `systemctl status 'iptsd@*.service'`; test all display corners and pen pressure/tilt in a drawing application. | Accurate coordinates, working multitouch and pen events without daemon failures. |
| Wi-Fi | `nmcli device status`; connect and transfer data. Inspect ath12k errors. | Reliable connection and correct calibration/MAC handling. Record the actual band; Wi-Fi 7 capability is not proven by enumeration. |
| Bluetooth | `bluetoothctl show`; pair a known device and test it. | Stable pairing and data/input/audio as applicable. |
| Audio | `wpctl status`, `aplay -l`; play stereo audio at low volume and record/replay a microphone sample. | Both speakers and microphones operate. Raise volume cautiously while speaker protection remains unverified. |
| Power | Inspect battery/AC status with `upower`; inspect `/sys/power/mem_sleep`; suspend from GNOME and resume using Power. | Charge state updates and repeated suspend/resume succeeds. Save logs before and after each cycle. |
| Sensors | Run `monitor-sensor`, rotate the tablet and test GNOME rotation. | Correct orientation and automatic rotation. |
| USB-C | Test storage, charge and unplug/replug on both ports. | Stable supported USB data and charging. External display over USB4/docks remains an upstream limitation. |
| NPU/FastRPC | Inspect `/dev/fastrpc*` and kernel remoteproc logs. | Record enumeration only; device presence does not prove inference support. |
| Cameras | Inspect `v4l2-ctl --list-devices` and relevant camera logs if tools exist. | Document current unsupported state. No working video capture is claimed. |

## Installation validation

Anaconda and the official live session are preserved. Test an actual installation only on a selected expendable target after reviewing disk changes. Record whether the installed system contains the Surface kernel, modules, LCD DTB, firmware, services and a matching initramfs, and whether its UEFI entry boots. An installer launch alone does not validate installed boot or drivers.
