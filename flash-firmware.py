import subprocess
import sys
import struct
import os
import random
import requests
import hashlib
import time
import binascii
from termcolor import colored
import time
import platform
import pync

# if platform.system() != 'Darwin':
#     print(colored("Sorry, this is for Mac OS only", 'red'))
os.system('clear')
os.system("python3 -m pip install adafruit-ampy termcolor requests pync")
# os.system('git clone https://github.com/adafruit/ampy.git')

# Check for ampy
ampy_log = subprocess.getoutput('ampy --version')
print(ampy_log)
if 'version' not in ampy_log:
    print((colored("=> Ampy installation failed", 'red')))
    sys.exit()



# Load Saved Data
import json
try:
    saved_data = json.load(open("faraclass-devices-check.json"))
    sys.exit()
except:
    saved_data = {}


list_port = map(lambda x : x.strip().rstrip(), subprocess.getoutput("ls /dev/tty.*").splitlines())

def break_line(string):
    print()
    terminal_size = os.get_terminal_size()[0]
    _len = (terminal_size - len(string)) // 2 - 2
    print(colored('='*_len+' ' +string+' '+'='*_len, 'yellow'))


def update_device_worker(port):
    break_line("Step 1: Start workiing on {}".format(port))
    break_line("Step 2: Get MAC Address")
    try:
        mac_data = subprocess.getoutput("python3 -m esptool -p {} read_mac".format(port))
        for line in mac_data.splitlines():
            if line.startswith('MAC'):
                mac_address = line.split(' ')[-1]

        print('MAC Address: ', mac_address)
    except Exception as err:
        print(colored(err, 'red'))
        print(colored("The controller is used by other process, unplug and plug it again will solve", 'red'))
        sys.exit()

    break_line("Step 3: Generate Random Key")

    hexkey = saved_data.get(mac_address, None)
    if hexkey == None:
        key_bytes = bytearray([random.randrange(0, 255) for _ in range(16)])
        hexkey = binascii.hexlify(key_bytes).decode('utf8')
        print('Secret: {}'.format(hexkey))
        saved_data[mac_address] = hexkey


    break_line("Step 4: Request for pre-firmware build")
    try:
        req = requests.post('https://cloud.faraclass.com:1301/api/v5/prefirmware', json = {
            'device_mac': mac_address,
            'device_secret': hexkey,
            'device_type': 'Dot',
            'issuer': 'Carlos'
        }, timeout = 5)
        with open('start.mpy', 'wb') as f:
            f.write(req.content)
        print(colored("Core Files received : {} bytes".format(len(req.content))))
    except Exception as err:
        print(colored("Possibly network error", 'red'), err)
        sys.exit()



    break_line("Step 5: Create backup file for you device")
    try:
        print('We will create a snapshot image, as backup, just in case')
        name = input("BackupName: ")
        if len(name) == 0:
            raise OSError
        # filename = mac_address.replace(":", '_')
        filename = name
        print(colored("=> Creating Backup file : snapshot.{}.bin".format(name), 'magenta'))
        filename = time.strftime("snapshot.{}.bin".format(filename))

        os.system("python3 -m esptool -p {} -b 115200 read_flash 0x00  0x400000 {}".format(port, filename))
        print(colored("=> Backup file saved {}".format(filename), "magenta"))
    except Exception:
        pass


    break_line("Step 5: Downloading fresh firmware")
    # if ;esp32-idf3-20190125-v1.10.bi
    if 'esp32-idf3-20190125-v1.10.bin' not in os.listdir():
        try:
            req = requests.get('https://micropython.org/resources/firmware/esp32-idf3-20190125-v1.10.bin')
            with open('esp32-idf3-20190125-v1.10.bin', 'wb') as f:
                f.write(req.content)
            print(colored('=> MicroPython Firmware Received: {} bytes'.format(len(req.content)), 'magenta'))

        except Exception as err:
            print(colored("Can't download firmware", 'red'))
            sys.exit()
    else:
        print(colored("=> Used cached file: esp32-idf3-20190125-v1.10.bin", 'magenta'))


    break_line("Step 6: Formatting Device Flash")
    os.system("python3 -m esptool -p {} -b 115200 erase_flash".format(port))
    print(colored("=> Great :D, Everything is cleared", 'magenta'))

    break_line("Step 7: Burning Firmware")
    os.system("python3 -m esptool -p {} -b 115200 write_flash -z 0x1000 esp32-idf3-20190125-v1.10.bin".format(port))


    break_line("Step 8: Flasing Boot File ")
    time.sleep(13)
    os.system('ampy -p {} -d 5 put start.mpy'.format(port))

    with open('#system.uuid','w') as f:
        f.write(hexkey)
    os.system('ampy -p {} -d 5 put "#system.uuid"'.format(port))

    with open('boot.py', 'w') as f:
        f.write('import start')

    os.system('ampy -p {} -d 5 put boot.py'.format(port))
    print(colored("=> Firmware Flashed", "magenta"))
    # os.system("python3 -m esptool -p /dev/tty.SLAB_USBtoUART -b 115200 write_flash -z 0x1000 esp32-idf3-20190125-v1.10.bin")




    with open('faraclass-devices-check.json', 'w') as f:
        f.write(json.dumps(saved_data, indent = 4))


if '--port' not in sys.argv:
    list_port = list(map(lambda x : x.strip().rstrip(), subprocess.getoutput("ls /dev/tty.SLAB*").splitlines())) + list(map(lambda x : x.strip().rstrip(), subprocess.getoutput("ls /dev/tty.wch*").splitlines()))
    list_port = list(filter(lambda x: "No such file or directory" not in x, list_port))
    break_line("Step 1 : Checking for Connected Port")
    is_slab_available = False
    for i, port in enumerate(list_port):
        print(colored('[{}] {}'.format(i, port), 'green' if 'tty.SLAB_USBtoUART' not in port else 'magenta'))
        if 'tty.SLAB_USBtoUART' in port:
            is_slab_available = True
        if 'tty.wchusbserial' in port:
            is_slab_available = True


    if is_slab_available == False:
        print(colored("No USB Driver detected", 'red'))
        sys.exit()
    else:
        print(colored(" => USB Driver Found"))



    URLS = []
    for port in list_port:
        print('Port: ', port)
        URLS.append(port)

    for url in URLS:
        update_device_worker(port = url)

else:
    update_device_worker(sys.argv[-1])



# import concurrent.futures
# with concurrent.futures.ThreadPoolExecutor() as executor:
#     URLS = []
#     list_port = map(lambda x : x.strip().rstrip(), subprocess.getoutput("ls /dev/tty.SLAB*").splitlines())

#     for port in list_port:
#         print('Port: ', port)
#         URLS.append(port)

#     future_to_url = {executor.submit(update_device_worker, url): url for url in URLS}
#     print(future_to_url)
#     for future in concurrent.futures.as_completed(future_to_url):
#         url = future_to_url[future]
#         try:
#             data = future.result()
#         except Exception as exc:
#             print('%r generated an exception: %s' % (url, exc))
#         else:
#             print('%r page is %d bytes' % (url, len(data)))

pync.notify(title = "Firmware Updated", message = "Please send the file faraclass-devices-check.json")

print(colored("""
    When you are done with ALL your device, please send me the faraclass-devices-check.json file
    We will need sometime to register those device to be valid.


    > Changes and notice
        > NEVER PRESS RESET BUTTON WHEN THE LED IS RED
        > The device will update its firmware when you press the reset button
        > It need wifi to do so, with prioritize as follow
            Last Wifi connected successfully by this device
            Hardcoded Wifi :    FaraClass  , password : faraclass
            List of wifi defined by CodeLAB

        
""", 'magenta'))