import time
import board
import busio
import digitalio
import adafruit_rfm9x
import EasyCrypt
import config

print("Intializing µPico")

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

rf = digitalio.DigitalInOut(board.GP7)
rf.direction = digitalio.Direction.OUTPUT

rf.value = False

RADIO_FREQ_MHZ = config.RADIO_FREQ_MHZ
CS = digitalio.DigitalInOut(board.GP21)
RESET = digitalio.DigitalInOut(board.GP20)
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Initialze RFM radio with a more conservative baudrate
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ, baudrate=1000000)

# You can however adjust the transmit power (in dB).  The default is 13 dB but
# high power radios like the RFM95 can go up to 23 dB:
rfm9x.tx_power = config.TX_POWER
rfm9x.signal_bandwidth = 62500
rfm9x.coding_rate = 6
rfm9x.spreading_factor = 8
rfm9x.enable_crc = True

# Wait to receive packets.
print("Waiting for packets...")
# We need to retreive count from file when starting if > ?? we do a rollover
file = open("remotecounter", "r")
remotecount = int(file.read())
file.close()
file = open("localcounter", "r")
count = int(file.read())
file.close()
while True:
    packet = rfm9x.receive(timeout=0.5)
    if packet is not None:
        decrypted = EasyCrypt.decrypt_string(config.DEVICE, packet, config.KEY)
        if decrypted is not False:
            print("Received (decrypted): {0}".format(decrypted))
            split = decrypted.split(',', 4)

            counter = int(split[0])
            type = str(split[1])
            port = int(split[2])
            state = str2bool(split[3])

            if counter > remotecount:
                try: 
                    file = open("remotecounter", "w")
                    file.write(str(counter))
                    file.close()
                except OSError:
                    print("Cannot write remotecounter, read-only fs")
                remotecount = counter

                rf.value = state
                value = str(count) + ',SW,' + str(rf.value)
                encrypted = EasyCrypt.encrypt_string(config.DEVICE, value, config.KEY)

                time_now = time.monotonic()
                rfm9x.send(encrypted)
                print("Send (encrypted): {0}".format(value))
                sleeptime = max(0, 0.45 - (time.monotonic() - time_now))
                time.sleep(sleeptime)
                count=count+1
                if count > 1000000:
                    count = 0
                try: 
                    file = open("localcounter", "w")
                    file.write(str(count))
                    file.close()
                except OSError:
                    print("Cannot write localcounter, read-only fs")
            else:
                print("Remote counter is to low ! attack ?!")