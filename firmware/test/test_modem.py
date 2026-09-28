import modem, time


#print("Modem power on")
#modem.power_on_off()
#time.sleep(10)
#print("Modem init")
#modem.modem_init()


while True:
 time.sleep(2)
# modem.send_at("AT+CBC","")
 modem.send_at("AT+CREG?","")
 modem.send_at("AT+CSQ","")
# modem.send_at("AT+CGATT?","")
 modem.send_at("AT+CENG=3,0", "OK")
 modem.send_at("AT+CENG?", "OK")
