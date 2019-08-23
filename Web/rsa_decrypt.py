import sys
import base64
import rsa
def decrypt_password(crypto):
    with open('private.pem') as privatefile:
        p = privatefile.read() # p is a string
    privkey = rsa.PrivateKey.load_pkcs1(p.encode('utf-8'))

    crypto = base64.b64decode(crypto)
    plaintext = rsa.decrypt(crypto,privkey) # is also byte
    return plaintext.decode()
