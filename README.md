# System Monitor Pro

System Monitor Pro is a comprehensive and user-friendly system monitoring application designed to provide real-time insights into your system's performance. With a sleek and customizable interface, it allows you to monitor CPU, memory, disk, GPU usage, running processes, and network connections. The application also supports threshold-based alerts, data export, and cloud integration.

## Features

- **Real-time Monitoring**: Track CPU, memory, disk, and GPU usage in real-time.
- **Process Management**: View and terminate running processes.
- **Network Monitoring**: Monitor active network connections.
- **Customizable Alerts**: Set thresholds for CPU, memory, disk, and GPU usage to receive notifications.
- **Data Export**: Save monitoring data in CSV or JSON format.
- **Cloud Integration**: Upload logs to AWS S3 for backup and analysis.
- **Multi-language Support**: Available in English and Russian.
- **Themes**: Choose between dark and light themes.

## Installation

1. **Clone the repository:**
  ```bash
  git clone https://github.com/yourusername/system-monitor-pro.git
  cd system-monitor-pro
  ```
   
2. **Run the application:**
  ```bash
  python main.py
  ```

## Usage

- **Overview Tab**: Displays real-time graphs and progress bars for CPU, memory, disk, and GPU usage.
- **Processes Tab**: Lists all running processes with options to terminate them.
- **Network Tab**: Shows active network connections.
- **Notifications Tab**: Displays alerts and notifications based on set thresholds.
- **Settings Tab**: Configure thresholds, update intervals, themes, and language.
- **System Info Tab**: Provides detailed information about the system.

## Configuration

The application uses a `config.json` file to store settings. You can manually edit this file or use the settings tab in the application to modify:

- **CPU, memory, disk, GPU thresholds**: Set custom thresholds for system resource usage.
- **Update interval**: Adjust the frequency of data updates.
- **Theme**: Choose between dark and light themes.
- **Language**: Switch between English and Russian.
- **AWS credentials**: Configure credentials for cloud integration (e.g., AWS S3).
