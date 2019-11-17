#!/usr/bin/python3

# ////////////////////////////////////////////////////////////////////
# import used to check and and set up the usb device during boot.
from os import system
from os import chmod
from time import sleep
import csv

# Import helper functions, we want all of them.
import auxFunctions

# Imports for working with the hardware/ICs.
import board
import busio
import RPi.GPIO as GPIO

#Used to talk to the i2c bus.
import adafruit_tca9548a

# Used for talking to the oled
from digitalio import DigitalInOut
import adafruit_ssd1306

# Used for the Barometer
import adafruit_mpl3115a2

# Used for the RTC (Real Time Clock)
import adafruit_ds3231


#////////////////////////////////////////////////////////////////////////////////
# Create a CONSTANT varaible that will be used to check the USB idVendor to make sure it is the correct device
# NOTE: if you want to use a different USB drive then find the usb idVendor tag.
#       This can be done by running command ( tail -f /var/log/messages ) in the Raspberry Pi console and plugging in the usb
#       Look for the debug message that contains the idVendor tag and change this constant to that tag.
VENDOR_ID = '0781'

# CONSTANT MOUNTING LOCATION
MOUNT_DIR = "/home/pi/usb"

# Constant used for the time between writes to the file.
TIME_BETWEEN_LINES = 60


# /////////////////////////////////////////////////////////////
# Set up each of the devices so that they are usable throughout the script.

i2c = busio.I2C(board.SCL, board.SDA)

# Create the TCA9548A object and give it the I2C bus (This is the I2C mux)
tca = adafruit_tca9548a.TCA9548A(i2c)

# Used to talk to the ds3231 (RTC) note, this is connected to mux channel 2 
rtc = adafruit_ds3231.DS3231(tca[2])

# 1 Out of the 2 MPL sensors for pressure and heat.
mpl1 = adafruit_mpl3115a2.MPL3115A2(tca[0]) # mux channel 0
mpl2 = adafruit_mpl3115a2.MPL3115A2(tca[1]) # mux channel 1

# Define LCD display dimensions and I2C address
WIDTH = 128
HEIGHT = 32

# Create the digital out used for display reset
rst = DigitalInOut(board.D7)

display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3c, reset=rst)

# Setup GPIO 14 for the button.
GPIO.setup(14, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# //////////////////////////////////////////////////////////////////////
# Clear the screen while running.
system('clear')


# Loop until usb device is found.
while 1:
    # Holds the device_node variable that will be used to map the usb
    # file system to a location on the raspberry pi so python can write to it.
    file_path = auxFunctions.check_usb(VENDOR_ID)

    # If there was a file_path found then we want to mount the USB
    if file_path:
        print("Attempting To Mount USB To: %s" % MOUNT_DIR)
        system('./mount.sh %s %s' % (file_path, MOUNT_DIR))

        # Give oled output
        display.fill(0) 
        display.text("Mount on %s" % MOUNT_DIR,0,0,1)
        display.text("Press Record Button",0,10,1)
        display.text("To Begin",0,20,1)
        display.show()
        # Break out of the usb loop
        break
    else:
        print("No USB Present...")
        print("Sleeping for 3 seconds then trying again.")
        # Give oled output
        display.fill(0) 
        display.text("No USB Present...",0,0,1)
        display.show()
        # Sleep for 10
        sleep(3)



#Check if the user needs to reset the clock:
if rtc.lost_power:
    auxFunctions.reset_rtc(rtc,display)

# Sleep Before going into record mode!
# This acts a debounce for the button!
sleep(1)
# At this point we are ready to collect data from the Devices.
# We first want to open and start to write to a file This file will be named the year then day
# Note that this is inside of a large try statement. This should handle if the user
# Unplugs the usb without pressing the stop recording button.
try:
    print('Starting Data Collection!')
    currentTime = rtc.datetime
    filename = "%s-%s-%s_%s_%s.csv" % (currentTime.tm_mon, currentTime.tm_mday,
                                        currentTime.tm_year, currentTime.tm_hour,
                                        currentTime.tm_min)
    count = 0
    with open(MOUNT_DIR + "/" + filename, "w", newline ='') as f:
        #Set up the CSV writer and write headers for the file.
        csv_writer = csv.writer(f, delimiter = ",")
        csv_writer.writerow(["Date", "Time", "Pressure 1", "Temperature 1", "Pressure 2", "Temperature 2"])
        #Grab the current time in sec
        #Note that Time_sec is (time_elasped, time)
        time_sec = auxFunctions.get_current_time(rtc)

        #Handle Starting
        display.fill(0)
        display.text("Currently Recording",0,0,1)
        display.text("Count: %s" % count, 0,10,1)
        display.text("Button To Stop",0,20,1)
        display.show()

    # Loop forever until the user presses the button.
    while 1:
        # Check if we can write to the file yet. rewrite the time elapsed
        # Check if enough time has passed
        if auxFunctions.time_elapsed(time_sec,rtc) >= TIME_BETWEEN_LINES:
            currentTime = rtc.datetime
            date = "%s-%s-%s" % (currentTime.tm_mon, currentTime.tm_mday,currentTime.tm_year,)
            time = "%s:%s.%s" % (currentTime.tm_hour, currentTime.tm_min,currentTime.tm_sec)

            with open(MOUNT_DIR + "/" + filename, "a", newline ='') as f:
                #Take both the mpl sensor reading and store them in tuples, (pressure, temperature, altitude)
                mpl1_data = (mpl1.pressure, mpl1.temperature, mpl1.altitude)
                mpl2_data = (mpl2.pressure, mpl2.temperature, mpl2.altitude)
                #Write data to the file .
                csv_writer = csv.writer(f, delimiter = ',')
                csv_writer.writerow([date, time, mpl1_data[0], mpl1_data[1], mpl2_data[0], mpl2_data[1]])
                count += 1

                #Handle output to lcd
                display.fill(0)
                display.text("Currently Recording",0,0,1)
                display.text("Count: %s" % count, 0,10,1)
                display.text("Button To Stop",0,20,1)
                display.show()
                print("Sensor 1: \n\t Pressure: %s \t Temperature: %s " 
                                                    %  (mpl1_data[0], mpl1_data[1]))
                print("Sensor 2: \n\t Pressure: %s \t Temperature: %s " 
                                                    %  (mpl2_data[0], mpl2_data[1]))
                # Update time
                time_sec = auxFunctions.get_current_time(rtc)
        input_state = GPIO.input(14)
        if not input_state:
            print('Data Collection Complete!')
            break
    display.fill(0)
    display.text("Recording Finished!",0,0,1)
    display.show()


except Exception as e:
    print(e)

#Unmount the file directory so we can make sure our data is safe
system('./unmount.sh %s' % (file_path))
