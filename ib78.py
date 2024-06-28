import PySimpleGUI as sg
import serial
import time

cap_type = ["Aluminum Lytics","Double Layer Lytics","Tantalum Caps","Ceramic Caps","All Other Caps"]
cap_abrv = ["ALM","DBL","TAN","CER","AOC"]
tst_type = ["Cap Value","Cap Leakage (Curr)","Cap Leakage (Ohms)","Dielectric Absorption","Cap ESR"]
tst_abrv = ["CAP","LKI","LKR","D/A","ESR"]

# All the stuff inside your window.
layout = [
    [sg.Text('', size=(1)), sg.Text('Enter data for capacitor test', font='bold', size=(34)),sg.Text('Measurement Results', font='bold', size=(20))],
    [sg.Text('Select Cap type  ', size=(12)), sg.Combo(cap_type, size=(18),
	default_value=cap_type[0],key='cap_type'), sg.Text('', size=(5)), sg.Text('Capacity ', size=(10)), sg.Txt(size=(10), key='-CAP-')],
	[sg.Text('Working Voltage  ', size=(12)), sg.InputText(size=(8)), sg.Text('0V, 1 upto 999V', size=(15)), sg.Text('Leakage I', size=(10)), sg.Txt(size=(10), key='-LKI-')],
	[sg.Text('Capacitor value  ', size=(12)), sg.InputText(size=(8)), sg.Text('Add PF, UF or F', size=(15)), sg.Text('Leakage R', size=(10)), sg.Txt(size=(10), key='-LKR-')],
	[sg.Text('Tolerance + ', size=(12)), sg.InputText(size=(8)), sg.Text('Add +%', size=(15)), sg.Text('Dial/Absorb', size=(10)), sg.Txt(size=(10), key='-D/A-')],
	[sg.Text('Tolerance - ', size=(12)), sg.InputText(size=(8)), sg.Text('Add -%', size=(15)), sg.Text('ESR', size=(10)), sg.Txt(size=(10), key='-ESR-')],
	[sg.Text('Select Test type ', size=(12)), sg.Combo(tst_type, size=(18),
	default_value=tst_type[0],key='tst_type'), sg.Text('', size=(5)), sg.Checkbox('Run all above tests', default = False, key='run_all')],
    [sg.Button('Test'), sg.Button('Cancel'), sg.Button('Send'), sg.Text('', size=(18)), sg.Text('Status', size=(10)), sg.Txt(size=(10), key='-STS-') ]]

err_msg = ['Component Type selection error',
    'Entered value beyond range of unit',
    'Entered value beyond range of test',
    'Value beyond zeroing limit',
    'No Voltage entered',
    'Invalid IEEE command',
    'Component out of test range']

s = ['','','','','','']
x_out = ''
delay = 1.5
ack = 0
hdr = ''
dat = ''
g_b = ''

# configure the serial connections (the parameters differs on the device you are connecting to)
ib78 = serial.Serial(port="COM1", baudrate=9600, bytesize=8, xonxoff=True, timeout=1)

ib78.isOpen()

# Create the Window
window = sg.Window('LC102 - IB78 tester', layout)

# splits result string into various fields
def res_status(xdata):  
    hdr = xdata[:3]
    dat = xdata[4:15]
    g_b = xdata[16]

# translates code into text string
def err_txt(code):
    return err_msg[int(code) - 1]

# send data from ib78 to lc102 instrument 
def lc102_cmd(cmds):
    # read array for command to be send to lc102
    for y in range(0, 6):
        # suppress empty parameters which may upset instrument
        if cmds[y] != '':
            # suppress parameters we don't send for some measurement types
            if (#(not ((y == 0) and cmds[5] == 'CAP')) or
                #(not ((y == 1) and cmds[5] == 'CAP')) or
                (not ((y == 3) and any(cmds[5] in x  for x in ['LKI','LKR']))) or
                (not ((y == 4) and any(cmds[5] in x  for x in ['LKI','LKR'])))):
                #print( str.encode(cmds[y] + '\n ') + str.encode(str(y)))
                ib78.write(str.encode(cmds[y] + '\r\n'))
                # allow instrument processing time, it's not that fast !!
                time.sleep(delay)
    #time.sleep(delay * 2)
    #ib78.write(str.encode('NFC' + '\r\n'))
    ack = 0

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read(timeout=1)
    if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
        break

    # used as temporary command option
    if event == 'Send':
        ib78.flush()
        #ib78.write(str.encode(str(18) + '\n'))
        ib78.write(str.encode('0V' + '\r\n'))
        ib78.write(str.encode('END' + '\r\n'))
        #ib78.write(str.encode('CPO' + '\n'))
        print('send')

    # processes the response data from instrument and fills in measurement values
    if ib78.inWaiting() > 0:
        x_out += ib78.read(1).decode('ascii')
        pos = x_out.find('\n')
        if pos > 0:
            # got at least one response back, process it
            if any(x_out[:3] in x  for x in ['ERR']):
                window['-STS-'].update(err_txt(x_out[5]))
                print(err_txt(x_out[5]))
                ack = -1
            elif any(x_out[:3] in x  for x in ['CPO','NFC']):
                # remove those response as these are instrument acknowledges
                #window['-STS-'].update(x_out[:pos])
                x_out = x_out[pos + 1:]
                ack = 1
            elif any(x_out[:3] in x  for x in ['CAP','LKI','LKR','D/A','ESR']):
                print('Measured %s value %s' % (x_out[:3], x_out[4:pos]))
                #window['-STS-'].update(x_out[:pos])
                # obtain value's from measurement & update window
                if x_out[:3] == 'CAP':
                    window['-CAP-'].update(x_out[4:pos])
                if x_out[:3] == 'LKI':
                    window['-LKI-'].update(x_out[4:pos])
                if x_out[:3] == 'LKR':
                    window['-LKR-'].update(x_out[4:pos])
                if x_out[:3] == 'D/A':
                    window['-D/A-'].update(x_out[4:pos])
                if x_out[:3] == 'ESR':
                    window['-ESR-'].update(x_out[4:pos])
                x_out = x_out[pos + 1:]
                ack = 2
            window.refresh()	
		
    # processes the test command button and starts measurement			
    if event == 'Test':
        idx = 0
        ack = -2
        for val in values:
            #print(str(val))
            if str(val) != 'run_all':
                if str(val) == 'cap_type':
                    s[idx] = cap_abrv[cap_type.index(values[val])]
                elif str(val) == 'tst_type':
                    s[idx] = tst_abrv[tst_type.index(values[val])]
                else:
                    s[idx] = values[val]
                idx = idx + 1
        # test for previous command completed else wait
        while(ack == 0):
            pass # todo add time out mechanism
        # switch between selected tests one or all
        if idx == 6 and values['run_all'] == True:
            for x_cmd in tst_abrv:
                #time.sleep(.2)
                s[5] = x_cmd
                lc102_cmd(s)
                print('Command\'s send ', s)
        else:
            # Send paramters to LC102
            lc102_cmd(s)
            print('Command send ', s)

        # send 'Control Panel On' command
        #lc102_cmd('CPO')

ib78.write(str.encode('CPO' + '\r\n'))
ib78.close()
window.close()