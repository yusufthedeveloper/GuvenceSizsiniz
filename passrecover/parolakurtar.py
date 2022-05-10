from cryptography.fernet import Fernet
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-tkn", required=True,help="sayi giriniz")
args = vars(ap.parse_args())

token = str(args["tkn"])
ll = open("token.key", "r")
apinmsr = ll
rsg = apinmsr.read()
f = Fernet(rsg)

apinmsr.close()
hh = bytes(token, encoding='utf8')
decryp = f.decrypt(hh)
print(str(decryp).split("'")[1])