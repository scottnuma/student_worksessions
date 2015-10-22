#!/usr/bin/env python
import usb.core
import struct

"""Lower-level (libusb) code to interface with RFID reader"""
class RFIDReaderUSB(object):
    """Try to connect libusb to the RFID reader device. May throw exceptions on errors."""
    def __init__(self, idVendor = 0x0c27, idProduct = 0x3bfa):
        dev = usb.core.find(idVendor = idVendor, idProduct = idProduct)
        if dev == None:
            raise Exception("Could not find RFID reader device (idVendor=%d, idProduct=%d)" % (idVendor, idProduct))
        try:
            dev.detach_kernel_driver(0)
        except usb.USBError:
            pass
        except NotImplementedError:
            pass
        self._dev = dev

    """Send a command to the card reader. Do not try to read anything back."""
    def send_bytes(self, cmd):
        assert len(cmd) == 8, "Must send only 8 bytes"
        #feature report out, id = 0
        self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)

    """Send a command to the card reader and read 8 bytes of reply back."""
    def exchange_bytes(self, cmd):
        assert len(cmd) == 8, "Must send only 8 bytes"
        #feature report out, id = 0
        self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)
        #feature report in, id = 1
        return self._dev.ctrl_transfer(0xa1, 0x01, 0x0301, 0, 8)

"""Higher-level (protocol) code to interface with RFID reader"""
class RFIDReader(object):
    COMMAND_GET_CARD_ID                = "\x8f\x00\x00\x00\x00\x00\x00\x00"
    COMMAND_GET_CARD_ID_32             = "\x8d%c\x00\x00\x00\x00\x00\x00"
    COMMAND_GET_CARD_ID_EXTRA_INFO     = "\x8e\x00\x00\x00\x00\x00\x00\x00"
    COMMAND_BEEP                       = "\x8c\x03%c\x00\x00\x00\x00\x00"
    COMMAND_GET_MODEL                  = "\x8c\x01%c\x00\x00\x00\x00\x00"
    COMMAND_CONFIG_FIELD_82            = "\x82\x00\x00\x00\x00\x00\x00\x00"
    COMMAND_GET_VERSION                = "\x8a\x00\x00\x00\x00\x00\x00\x00"

    """Construct a RFIDReader. Must be passed an instance of an RFIDReaderUSB (or possibly equivalent)."""
    def __init__(self, llInterface):
        assert llInterface != None, "Need to supply llInterface"
        self._ll = llInterface

    """Return a card id up to 64 bits."""
    def get_card_id(self):
        card_id = self._ll.exchange_bytes(RFIDReader.COMMAND_GET_CARD_ID)[::-1]
        return ''.join((chr(x) for x in card_id))

    """Return a card id up to 256 bits."""
    def get_card_id_32(self):
        def get_card_id_32_internal(ll, i):
            card_id = ll.exchange_bytes(RFIDReader.COMMAND_GET_CARD_ID_32 % i)[::-1]
            return ''.join((chr(x) for x in card_id))
        id32_0 = get_card_id_32_internal(self._ll, 0)
        id32_1 = get_card_id_32_internal(self._ll, 1)
        id32_2 = get_card_id_32_internal(self._ll, 2)
        id32_3 = get_card_id_32_internal(self._ll, 3)
        return id32_3 + id32_2 + id32_1 + id32_0

    """Make the card reader beep."""
    def beep(self, num_beeps=1, long_beeps=False):
        #TODO: why read?
        assert num_beeps >= 1 and num_beeps <= 7, "Beeps must be between 1 and 7"
        self._ll.exchange_bytes(RFIDReader.COMMAND_BEEP % (num_beeps + (0x80 if long_beeps else 0)))

    """Get the model of the card reader. May be padded with null bytes."""
    def get_model(self):
        def get_model_internal(ll, i):
            card_id = ll.exchange_bytes(RFIDReader.COMMAND_GET_MODEL % i)
            return ''.join((chr(x) for x in card_id))
        model1 = get_model_internal(self._ll, 0)
        model2 = get_model_internal(self._ll, 1)
        model3 = get_model_internal(self._ll, 2)
        return model1 + model2 + model3

    """Return a word (16 bits) of data somehow associated with the card scan. Purpose unclear; may be card type. Only works after get_card_id."""
    def get_additional_id_info(self):
        card_id = self._ll.exchange_bytes(RFIDReader.COMMAND_GET_CARD_ID_EXTRA_INFO)
        return struct.unpack("<H", ''.join((chr(x) for x in card_id[:2])))[0]

    """Allow LED to be automatically controlled."""
    def set_led_auto(self):
        old_data = self._ll.exchange_bytes(RFIDReader.COMMAND_CONFIG_FIELD_82)
        old_data[0] = 0
        old_data[1] = old_data[1] & 0xFD
        self._ll.send_bytes(RFIDReader.COMMAND_CONFIG_FIELD_82)
        self._ll.send_bytes(old_data)
    """Override the LED into a particular state. Combining red and green gives amber."""
    def set_led_state(self, red, green):
        old_data = self._ll.exchange_bytes(RFIDReader.COMMAND_CONFIG_FIELD_82)
        old_data[0] = ((1 if red else 0) | (2 if green else 0))
        old_data[1] = old_data[1] | 0x02
        self._ll.send_bytes(RFIDReader.COMMAND_CONFIG_FIELD_82)
        self._ll.send_bytes(old_data)

    """Get version information about the reader. The first two bytes are LUID. The next two bytes are the firmware version. The other bytes are unknown."""
    def get_version(self):
        ver = self._ll.exchange_bytes(RFIDReader.COMMAND_GET_VERSION)
        return ''.join((chr(x) for x in ver))

def hex_to_dec(hex_num):
    """Takes a hexadecimal number (in the form of a string) and returns the decimal integer corresponding to it."""
    hd_dict = {'0':0, '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15}
    hex_num = hex_num[::-1]
    dec_num = 0
    for i in range(len(hex_num)):
        dec_num += hd_dict[hex_num[i]] * pow(16, i)
    return dec_num

def raw_card_info(rdr):
    """Returns the raw data for the card currently on the scanner as a string.  If there is no card, will return 0000000000000001."""
    return str(binascii.hexlify(rdr.get_card_id()))

def dec_card_id(rdr):
    """Returns the six numbers on the back of the Cal1 card currently on the scanner, or None if no card is present."""
    hex_id_str = raw_card_info(rdr)
    if(hex_id_str == '0000000000000001'):
        return None
    return(hex_to_dec(hex_id_str[9:14])) # These are the digits that actually store the numbers on the card

def wait_until_card(rdr):
    """Waits until a card is swiped, then returns the six numbers on the back."""
    card_id = None
    while not card_id:
        card_id = dec_card_id(rdr)
    return card_id

def wait_until_none(rdr):
    """Waits until there is no card on the scanner, then returns."""
    card_id = dec_card_id(rdr)
    while card_id:
        card_id = dec_card_id(rdr)

def time_stamp():
    """Returns the current time in the form year-month-day hour:minute:second"""
    import time
    import datetime
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

#TODO: convert to actual code
def main():
    """Continually waits for a card to be swiped, then inputs the name of the card holder into the check in spreadsheet."""
    # authenticate / login / open spreadsheets
    rdr = RFIDReader(RFIDReaderUSB())

    while True:
        card_id = wait_until_card(rdr)
        time = time_stamp()
        # convert from card id to name
        # write name and time to spreadsheet
        wait_until_none(rdr)


if __name__=="__main__":
    rdr = RFIDReader(RFIDReaderUSB())

    import binascii
    import time
    import sys

    print('Starting...')
    sys.stdout.flush()

    while True:
        card_id = wait_until_card(rdr)
        print('Card on reader: ' + str(card_id))
        print('Raw data: ' + raw_card_info(rdr))
        print(time_stamp())
        sys.stdout.flush()
        wait_until_none(rdr)
        print('Card off the reader.')
        sys.stdout.flush()