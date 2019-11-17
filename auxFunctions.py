import pyudev
import readchar
import time
# Checks if the usb is present will return the device file
# If the usb is not detected then will return None
def check_usb(VENDOR_ID):
    # Create a required context to scan the devices attached to the pi
    context = pyudev.Context()
    file_path = None
    # Note we could attempt to access the device instantly but checking this way will make sure we can find the device
    for device in context.list_devices(subsystem='block', DEVTYPE='partition'):
        #if the vendor ids match on the usb then we want to set the file_path to the device file
        if device.get("ID_VENDOR_ID") == VENDOR_ID:
            file_path = device.device_node
    return file_path

# Used to check if the time has passed long enough to take another reading.
# Will return the time elapsed in seconds and the current time in seconds (elap, cur)
# This function could really use some work on the algorithm.
def time_elapsed(pTime,rtc):
    currentTime = rtc.datetime
    f_hour = currentTime.tm_hour
    f_min = currentTime.tm_min
    f_sec = currentTime.tm_sec
    # Grab current time in seconds
    cTime = (f_hour * 3600) + (f_min * 60) + (f_sec)
    # note is this (-) then we have a roll over in the clock
    elapsed_time = cTime - pTime
    # Then we need to account for this.
    if elapsed_time < 0:
        # Subtract off the full 24 hours roll over and fix it.
        elapsed_time = 86400 - elapsed_time
    return elapsed_time

# This function will return the current time in seconds to be used in time elasped
def get_current_time(rtc):
    currentTime = rtc.datetime
    f_hour = currentTime.tm_hour
    f_min = currentTime.tm_min
    f_sec = currentTime.tm_sec
    return (f_hour * 3600) + (f_min * 60) + (f_sec)

# Handles displaying the string that the user is typing as they input a number.
def _input_capture_loop(display):
    input_str = ""
    print("Your Current String:")
    #Loop until the user pressed Enter on the keyboard.
    while 1:
        #Let the user know the date format, and print their string.
        display.fill(0) 
        display.text("Enter Date Format",0,0,1)
        display.text("mm/dd/yyyy/hh/mm/ss",0,10,1)
        display.text(input_str,0,20,1)
        display.show()
        print(input_str)
        #Read the char from the buffer.
        c = readchar.readchar()

        #If the user pressed backspace then we want to pop the last char off the input str
        if ord(c) == 127:
            input_str = input_str[:-1]
        # If the user pressed enter we know they wanted to submit their string.
        elif ord(c) == 13:
            break
        else:
            # Add to the string.
            input_str = input_str + c
    return input_str  
    
#Lets the user reset the RTC
def reset_rtc(rtc, display):

    # Lets the user know that power was lost.
    display.fill(0) 
    display.text("Power to RTC Was Lost",0,0,1)
    display.text("Please Press Enter",0,10,1)
    display.text("To Re-program rtc",0,20,1)
    display.show()
    input()
    print("Power Was lost to RTC")
    print("Please Press Enter To reprogram")

    updated = False
    while not updated:
        #Take the input from the user. 
        input_str = _input_capture_loop(display) 
        try:
            # Attempt to parse all of the user's data into integers
            t = [int(i) for i in input_str.split("/")]
            
            #Attempt to write the data into the datetime value. 
            #Note: year, month, .day, hour, minute, second, 0,0,0
            rtc.datetime = time.struct_time((t[2], t[0], t[1], t[3], t[4], t[5], 0,0,0))

            #If both are done then we can finish this loop and know the datetime is set!
            updated = True
        except Exception as e:
            print(e)
            #let the user know the input was invalid.
            display.fill(0) 
            display.text("Input Provided was invalid!",0,0,1)
            display.text("Please Re-enter",0,10,1)
            display.show()
            print("Input Was invalid.")
            input("Press Enter To Start")

