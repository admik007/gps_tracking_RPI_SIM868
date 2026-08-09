import utime, time, ntptime, binascii, ubinascii, network, machine, socket, dht, os, framebuf, uos, sys
import time
from machine import Pin, UART, I2C, ADC, WDT, SPI, PWM
import sdcard


SD = True

if (SD == True):
 # SPI configuration for SPI0
 spi = machine.SPI(0,baudrate=100_000, polarity=0, phase=0, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
 cs = machine.Pin(17, machine.Pin.OUT)
 cs.value(1)  # deselect SD card initially
 PATHA="/sd"
 # INITIALIZE SD CARD
 sd = sdcard.SDCard(spi, cs)
 # MOUNT THE FILESYSTEM
 vfs = uos.VfsFat(sd)
 uos.mount(vfs, PATHA)
else:
 PATHA=""

# DEFINE LED 
led = machine.Pin("LED", machine.Pin.OUT)
led.value(0)

for x in os.listdir(PATHA):
 print(PATHA+"/"+x)