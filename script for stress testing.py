import psutil
import datetime
import time
import subprocess
import os
import logging
import GPUtil
import cpuinfo

# Set up logging
logging.basicConfig(filename='temp_log.csv', level=logging.INFO, format='%(asctime)s, %(message)s')
logger = logging.getLogger()

# Set critical temperatures
CPU_CRITICAL_TEMP = 37  # degrees Celsius
GPU_CRITICAL_TEMP = 32  # degrees Celsius

def get_gpu_temp():
    return GPUtil.getGPUs()[0].temperature

def get_cpu_temp():
    return psutil.sensors_temperatures()['coretemp'][0][1]

def stress_test_cpu():
    print("Stress testing CPU...")
    subprocess.run(['stress-ng', '-c', '4', '-t', '60', '--perf'])

def stress_test_gpu():
    print("Stress testing GPU...")
    subprocess.run(['stress-ng', '-c', '1', '-t', '60', '--perf'])

def main():
    while True:
        print("\nOptions:")
        print("1. Stress test CPU and GPU")
        print("2. Log temperatures only")
        print("3. Quit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            print("Stress testing...")
            stress_test_cpu()
            stress_test_gpu()
        elif choice == "2":
            print("Logging temperatures...")
            while True:
                cpu_temp = get_cpu_temp()
                gpu_temp = get_gpu_temp()
                
                if cpu_temp > CPU_CRITICAL_TEMP or gpu_temp > GPU_CRITICAL_TEMP:
                    logger.info(f"CPU Temperature: {cpu_temp}°C")
                    logger.info(f"GPU Temperature: {gpu_temp}°C")
                    print(f"CPU Temperature: {cpu_temp}°C")
                    print(f"GPU Temperature: {gpu_temp}°C")
                
                time.sleep(10)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()