import machine, time, random, utime, config
from machine import WDT, Pin
#####################################################################
#####################  DEFINITION OF FUNCTIONS  #####################
WD = False

TIMEOUT = 1000

MQTT_HOST = config.MQTT_HOST
MQTT_PORT = config.MQTT_PORT

led = machine.Pin("LED", machine.Pin.OUT)

if (WD == True):
 wdt=WDT(timeout=8388)

# WAIT RESPONSE INFO
def wait_resp_info(timeout=TIMEOUT):
 prvmills = utime.ticks_ms()
 info = b""
 while (utime.ticks_ms()-prvmills) < timeout:
  if (WD == True):
   wdt.feed()
  led.toggle()
  if gsm_module.any():
   info = b"".join([info, gsm_module.read(1)])
 return info


# SEND AT COMMAND
def send_at(cmd, back, timeout=TIMEOUT):
 t_start = utime.ticks_ms()
 rec_buff = b''
 gsm_module.write((cmd + '\r\n').encode())
 while utime.ticks_diff(utime.ticks_ms(), t_start) < timeout:
  if (WD == True):
   wdt.feed()
  led.toggle()
  if gsm_module.any():
   chunk = gsm_module.read()
   if chunk:
    rec_buff += chunk
    # ---------------------------------
    # EXPECTED RESPONSE RECEIVED
    # ---------------------------------
    if back == "" or back in rec_buff.decode():
     print(rec_buff.decode())
     print(
      "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
       cmd,
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ),
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ) / 1000
      )
     )
     return True

    # ---------------------------------
    # ERROR RESPONSE
    # ---------------------------------
    if (
     b"ERROR" in rec_buff
     or
     b"FAIL" in rec_buff
    ):
     print(rec_buff.decode())
     print(
      "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
       cmd,
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ),
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ) / 1000
      )
     )

     return False

 # ---------------------------------
 # TIMEOUT
 # ---------------------------------
 print(
  cmd + " TIMEOUT:",
  rec_buff.decode()
 )
 print(
  "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
   cmd,
   utime.ticks_diff(
    utime.ticks_ms(),
    t_start
   ),
   utime.ticks_diff(
    utime.ticks_ms(),
    t_start
   ) / 1000
  )
 )
 return False



# SEND AT COMMAND AND RETURN RESPONSE INFORMATION
def send_at_get_response(cmd, back, timeout=TIMEOUT):
 t_start = utime.ticks_ms()
 rec_buff = b''
 gsm_module.write((cmd + '\r\n').encode())
 while utime.ticks_diff(utime.ticks_ms(), t_start) < timeout:
  if (WD == True):
   wdt.feed()
  led.toggle()
  if gsm_module.any():
   chunk = gsm_module.read()
   if chunk:
    rec_buff += chunk
    text = rec_buff.decode()
    # ---------------------------------
    # EXPECTED RESPONSE RECEIVED
    # ---------------------------------
    if back == "" or back in text:
     print(text)
     print(
      "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
       cmd,
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ),
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ) / 1000
      )
     )
     return rec_buff

    # ---------------------------------
    # ERROR
    # ---------------------------------
    if (
     b"ERROR" in rec_buff
     or
     b"FAIL" in rec_buff
    ):
     print(text)
     print(
      "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
       cmd,
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ),
       utime.ticks_diff(
        utime.ticks_ms(),
        t_start
       ) / 1000
      )
     )
     return rec_buff

 # ---------------------------------
 # TIMEOUT
 # ---------------------------------
 print(
  cmd + " TIMEOUT:",
  rec_buff.decode()
 )
 print(
  "[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
   cmd,
   utime.ticks_diff(
    utime.ticks_ms(),
    t_start
   ),
   utime.ticks_diff(
    utime.ticks_ms(),
    t_start
   ) / 1000
  )
 )
 return rec_buff


def send_at_get_response2(cmd, back, timeout=TIMEOUT):
 rec_buff = b''
 gsm_module.write((cmd + '\r\n').encode())
 prvmills = utime.ticks_ms()
 while (utime.ticks_ms() - prvmills) < timeout:
  wdt.feed()
  if (WD == True):
   wdt.feed()
  if gsm_module.any():
   rec_buff = b"".join([rec_buff, gsm_module.read(1)])
 if len(rec_buff) > 0:
  response = rec_buff.decode()
  if back not in response:
   print(cmd + ' back:\t' + rec_buff.decode())
  else:
   print(rec_buff.decode())
 else:
  print(cmd + ' no responce')
  print("Response information is: ", rec_buff)
 return rec_buff


def tcp_send(data):
 t_total = time.ticks_ms()
 length = len(data)
 print("TCP SEND length:", length)
 # =================================
 # CIPSEND
 # =================================
 t = time.ticks_ms()
 gsm_module.write(
  ("AT+CIPSEND=" + str(length) + "\r\n").encode()
 )
 print(
  "[TIME] CIPSEND command:",
  time.ticks_diff(time.ticks_ms(), t),
  "ms"
 )
 # =================================
 # WAIT FOR >
 # =================================
 t = time.ticks_ms()
 response = b""
 while time.ticks_diff(time.ticks_ms(), t) < 5000:
  if (WD == True):
   wdt.feed()
  led.toggle()
  if gsm_module.any():
   chunk = gsm_module.read()
   if chunk:
    response += chunk
    if b">" in response:
     break
  time.sleep_ms(1)
 print("CIPSEND RX:", response)
 if b">" not in response:
  print("CIPSEND prompt timeout")
  print(
   "[TIME] TCP SEND TOTAL:",
   time.ticks_diff(time.ticks_ms(), t_total),
   "ms"
  )
  return False
 print(
  "[TIME] WAIT FOR >:",
  time.ticks_diff(time.ticks_ms(), t),
  "ms"
 )
 # =================================
 # SEND MQTT PACKET
 # =================================
 t = time.ticks_ms()
 total_written = 0
 while total_written < length:
  written = gsm_module.write(
   data[total_written:]
  )
  if written is None or written <= 0:
   time.sleep_ms(1)
   continue
  total_written += written
 print(
  "[TIME] UART WRITE:",
  time.ticks_diff(time.ticks_ms(), t),
  "ms"
 )
 print(
  "UART total written:",
  total_written
 )
 # =================================
 # WAIT FOR SEND OK
 # =================================
 t = time.ticks_ms()
 response = b""
 while time.ticks_diff(time.ticks_ms(), t) < 10000:
  if (WD == True):
   wdt.feed()
  led.toggle()
  if gsm_module.any():
   chunk = gsm_module.read()
   if chunk:
    response += chunk
    print("SEND RX:", chunk)
    if b"SEND OK" in response:
     print(
      "[TIME] WAIT SEND RESULT:",
      time.ticks_diff(time.ticks_ms(), t),
      "ms"
     )
     print(
      "[TIME] TCP SEND TOTAL:",
      time.ticks_diff(
       time.ticks_ms(),
       t_total
      ),
      "ms"
     )
     return True
    if b"SEND FAIL" in response:
     print(
      "SEND FAIL:",
      response
     )
     return False
    if b"ERROR" in response:
     print(
      "SEND ERROR:",
      response
     )
     return False
  time.sleep_ms(1)
 print(
  "SEND TIMEOUT:",
  response
 )
 print(
  "[TIME] TCP SEND TOTAL:",
  time.ticks_diff(
   time.ticks_ms(),
   t_total
  ),
  "ms"
 )
 return False


# SIM868 CONFIGURATION
#sim_dtr = Pin(17, Pin.OUT)
sim_pwr = Pin(14, Pin.OUT)
uart_gsm_port = 0
uart_gsm_baute = 115200
gsm_module = machine.UART(uart_gsm_port, uart_gsm_baute)
print(gsm_module)


# POWER ON/OFF THE MODULE
def power_on_off():
 print('Power on')
 sim_pwr.value(1)
 print('Done')
 
 # ============================================================
# TIME MEASUREMENT HELPERS
# ============================================================

def ms():
 return time.ticks_ms()


def elapsed(start):
 return time.ticks_diff(time.ticks_ms(), start)


def print_step(name, start):
 print("[TIME] {:<25} {:>6} ms ({:.3f} s)".format(
  name,
  elapsed(start),
  elapsed(start) / 1000
 ))


# ============================================================
# MODEM INITIALIZATION
# ============================================================

def modem_init():

 init_start = ms()

 print("")
 print("========================================")
 print("MODEM INITIALIZATION")
 print("========================================")

 # -------------------------
 # MODEM
 # -------------------------

 if not send_at("AT", "OK"):
  print("Modem not responding")
  return False

 # -------------------------
 # SIM CARD
 # -------------------------

 if not send_at("AT+CPIN?", "OK"):
  print("SIM card not ready")
  return False

 # -------------------------
 # GSM NETWORK
 # -------------------------

 if not wait_for_network():
  print("No GSM network")
  return False

 # -------------------------
 # SIGNAL
 # -------------------------

 if not send_at("AT+CSQ", "OK"):
  print("CSQ failed")
  return False

 # -------------------------
 # GPRS ATTACH
 # -------------------------

 if not send_at("AT+CGATT?", "OK"):
  print("GPRS attach check failed")
  return False

 # -------------------------
 # GPRS DATA SESSION
 # -------------------------

 if not send_at(
  "AT+CIPSHUT",
  "SHUT OK",
  10000
 ):
  print("CIPSHUT failed")
  return False

 # krátka pauza môže zostať
 time.sleep_ms(200)

 if not send_at(
  'AT+CSTT="internet"',
  "OK"
 ):
  print("CSTT failed")
  return False

 time.sleep_ms(200)

 if not send_at(
  "AT+CIICR",
  "OK",
  10000
 ):
  print("CIICR failed")
  return False

 # Po CIICR nechaj modem chvíľu stabilizovať
 time.sleep_ms(500)

 if not send_at(
  "AT+CIFSR",
  "."
 ):
  print("CIFSR failed")
  return False

 time.sleep_ms(200)

 # -------------------------
 # TCP SOCKET
 # -------------------------

 if not send_at(
  'AT+CIPSTART="TCP","'+MQTT_HOST+'","'+MQTT_PORT+'"',
  "CONNECT OK",
  20000
 ):
  print("TCP connection failed")
  return False

 time.sleep_ms(200)

 # -------------------------
 # STATUS
 # -------------------------

 send_at(
  "AT+CIPSTATUS",
  "STATE:",
  3000
 )
 # -------------------------
 # TOTAL
 # -------------------------
 total = elapsed(init_start)
 print("")
 print("========================================")
 print("MODEM INITIALIZATION COMPLETE")
 print(
  "TOTAL TIME: {} ms ({:.3f} s)".format(
   total,
   total / 1000
  )
 )
 print("========================================")
 print("Modem initialization successful")
 return True


def modem_init2():

 init_start = ms()

 print("")
 print("========================================")
 print("MODEM INITIALIZATION")
 print("========================================")

 # -------------------------
 # MODEM
 # -------------------------
 t = ms()

 if not send_at("AT", "OK"):
  print("Modem not responding")
  print_step("AT", t)
  return False

 print_step("AT", t)

 t = ms()
 time.sleep(1)
 print_step("sleep 1s", t)

 # -------------------------
 # SIM CARD
 # -------------------------
 t = ms()

 if not send_at("AT+CPIN?", "OK"):
  print("SIM card not ready")
  print_step("SIM CPIN", t)
  return False

 print_step("SIM CPIN", t)

 t = ms()
 time.sleep(1)
 print_step("sleep 1s", t)

 # -------------------------
 # GSM NETWORK
 # -------------------------
 t = ms()

 if not wait_for_network():
  print("No GSM network")
  print_step("WAIT GSM NETWORK", t)
  return False

 print_step("WAIT GSM NETWORK", t)

 # -------------------------
 # SIGNAL
 # -------------------------
 t = ms()

 if not send_at("AT+CSQ", "OK"):
  print("CSQ failed")
  print_step("CSQ", t)
  return False

 print_step("CSQ", t)

 t = ms()
 time.sleep(1)
 print_step("sleep 1s", t)

 # -------------------------
 # GPRS ATTACH
 # -------------------------
 t = ms()

 if not send_at("AT+CGATT?", "OK"):
  print("GPRS attach check failed")
  print_step("CGATT?", t)
  return False

 print_step("CGATT?", t)

 t = ms()
 time.sleep(1)
 print_step("sleep 1s", t)

 # -------------------------
 # GPRS DATA SESSION
 # -------------------------

 # CIPSHUT
 t = ms()

 if not send_at(
  "AT+CIPSHUT",
  "SHUT OK",
  10000
 ):
  print("CIPSHUT failed")
  print_step("CIPSHUT", t)
  return False

 print_step("CIPSHUT", t)

 t = ms()
 time.sleep(.5)
 print_step("sleep .5s", t)

 # CSTT
 t = ms()

 if not send_at(
  'AT+CSTT="internet"',
  "OK"
 ):
  print("CSTT failed")
  print_step("CSTT", t)
  return False

 print_step("CSTT", t)

 t = ms()
 time.sleep(.5)
 print_step("sleep .5s", t)

 # CIICR
 t = ms()

 if not send_at(
  "AT+CIICR",
  "OK",
  10000
 ):
  print("CIICR failed")
  print_step("CIICR", t)
  return False

 print_step("CIICR", t)

 t = ms()
 time.sleep(2)
 print_step("sleep 2s", t)

 # CIFSR
 t = ms()

 if not send_at(
  "AT+CIFSR",
  "."
 ):
  print("CIFSR failed")
  print_step("CIFSR", t)
  return False

 print_step("CIFSR", t)

 t = ms()
 time.sleep(.5)
 print_step("sleep .5s", t)

 # -------------------------
 # TCP SOCKET
 # -------------------------
 t = ms()

 if not send_at(
  'AT+CIPSTART="TCP","'+MQTT_HOST+'","'+MQTT_PORT+'"',
  "CONNECT OK",
  20000
 ):
  print("TCP connection failed")
  print_step("CIPSTART", t)
  return False

 print_step("CIPSTART", t)

 t = ms()
 time.sleep(.5)
 print_step("sleep .5s", t)

 # CIPSTATUS
 t = ms()

 send_at(
  "AT+CIPSTATUS",
  ""
 )

 print_step("CIPSTATUS", t)

 t = ms()
 time.sleep(.5)
 print_step("sleep .5s", t)

 # -------------------------
 # TOTAL
 # -------------------------

 total = elapsed(init_start)

 print("")
 print("========================================")
 print("MODEM INITIALIZATION COMPLETE")
 print("TOTAL TIME: {} ms ({:.3f} s)".format(
  total,
  total / 1000
 ))
 print("========================================")

 print("Modem initialization successful")
 return True


# ============================================================
# NETWORK CHECK
# ============================================================

def check_network():

 t = ms()

 resp = send_at_get_response(
  "AT+CREG?",
  "OK"
 ).decode()

 print_step("check_network CREG", t)

 if "+CREG: 0,1" in resp:
  return True

 if "+CREG: 0,5" in resp:
  return True

 return False


# ============================================================
# WAITING FOR GSM NETWORK
# ============================================================

def wait_for_network(timeout=180):

 total_start = ms()

 print("Waiting for GSM network...")

 while elapsed(total_start) < timeout * 1000:

  t = ms()

  reg = send_at_get_response(
   "AT+CREG?",
   "OK"
  ).decode()

  print(reg)
  print_step("CREG query", t)

  if "+CREG: 0,1" in reg or "+CREG: 0,5" in reg:

   print("GSM registered")

   print(
    "[TIME] GSM registration total: {} ms ({:.3f} s)".format(
     elapsed(total_start),
     elapsed(total_start) / 1000
    )
   )

   return True

  t = ms()
  time.sleep_ms(500)
  print_step("network sleep .5s", t)

 print("Network timeout")

 print(
  "[TIME] GSM registration timeout: {} ms ({:.3f} s)".format(
   elapsed(total_start),
   elapsed(total_start) / 1000
  )
 )

 return False


# ============================================================
# GET NETWORK INFO
# ============================================================

def get_network_info():

 total_start = ms()

 csq = 0
 creg = 0
 cgatt = 0

 # -------------------------
 # SIGNAL QUALITY
 # -------------------------

 t = ms()

 response = send_at_get_response(
  "AT+CSQ",
  "OK"
 )

 print_step("AT+CSQ", t)

 try:
  text = response.decode()

  if "+CSQ:" in text:

   value = text.split(
    "+CSQ:"
   )[1].split(",")[0].strip()

   csq = int(value)

   # 99 = unknown
   if csq == 99:
    csq = 0

 except Exception:
  csq = 0

 # -------------------------
 # NETWORK REGISTRATION
 # -------------------------

 t = ms()

 response = send_at_get_response(
  "AT+CREG?",
  "OK"
 )

 print_step("AT+CREG?", t)

 try:
  text = response.decode()

  if "+CREG:" in text:

   value = text.split(
    "+CREG:"
   )[1].split(",")[1].split()[0]

   creg = int(value)

 except Exception:
  creg = 0

 # -------------------------
 # GPRS ATTACH
 # -------------------------

 t = ms()

 response = send_at_get_response(
  "AT+CGATT?",
  "OK"
 )

 print_step("AT+CGATT?", t)

 try:
  text = response.decode()

  if "+CGATT:" in text:

   value = text.split(
    "+CGATT:"
   )[1].split()[0]

   cgatt = int(value)

 except Exception:
  cgatt = 0

 # -------------------------
 # TOTAL
 # -------------------------

 print(
  "[TIME] get_network_info total: {} ms ({:.3f} s)".format(
   elapsed(total_start),
   elapsed(total_start) / 1000
  )
 )

 return {
  "csq": csq,
  "creg": creg,
  "cgatt": cgatt
 }


# MODEM RESET
def modem_reset():

 print("Resetting modem with AT+CFUN=1,1")

 gsm_module.write(
  b"AT+CFUN=1,1\r\n"
 )

 # SIM868 sa teraz môže reštartovať.
 # Odpoveď nemusí byť spoľahlivo dostupná.

 time.sleep(10)

 print("Modem reset wait completed")

 return True
#####################  DEFINITION OF FUNCTIONS  #####################
#####################################################################
