import os
import json
import base64
import hashlib
import secrets

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# RSA
# =========================

def gen_rsa_keys():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return priv, priv.public_key()


def pem_private(priv):
    return priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()


def pem_public(pub):
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def load_private(pem: str):
    return serialization.load_pem_private_key(pem.encode(), password=None)


def load_public(pem: str):
    return serialization.load_pem_public_key(pem.encode())


# AES-GCM (integridad real)
# =========================

def aes_encrypt(key, data: bytes):
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    enc = cipher.encryptor()
    ct = enc.update(data) + enc.finalize()
    return iv, ct, enc.tag


def aes_decrypt(key, iv, ct, tag):
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
    dec = cipher.decryptor()
    return dec.update(ct) + dec.finalize()


# =========================
# FILE ENCRYPTION
# =========================

def encrypt_file(path: str, pub_pem: str, overwrite=False) -> str:
    """
    Encripta un archivo usando AES-GCM y luego encripta la clave AES con RSA.
    Devuelve la ruta del archivo encriptado.
    """
    pub = load_public(pub_pem)

    data = open(path, "rb").read()
    aes_key = secrets.token_bytes(32)

    iv, ct, tag = aes_encrypt(aes_key, data)

    enc_key = pub.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    package = {
        "key": base64.b64encode(enc_key).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ct": base64.b64encode(ct).decode(),
        "tag": base64.b64encode(tag).decode()
    }

    if overwrite:
        out = path
    else:
        out = path + ".enc"
    
    open(out, "w").write(json.dumps(package))
    return out


def decrypt_file(path: str, priv_pem: str, overwrite=False) -> str:
    """
    Desencripta un archivo encriptado con encrypt_file.
    Devuelve la ruta del archivo desencriptado.
    """
    priv = load_private(priv_pem)

    pkg = json.loads(open(path, "r").read())

    enc_key = base64.b64decode(pkg["key"])
    iv = base64.b64decode(pkg["iv"])
    ct = base64.b64decode(pkg["ct"])
    tag = base64.b64decode(pkg["tag"])

    aes_key = priv.decrypt(
        enc_key,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    plain = aes_decrypt(aes_key, iv, ct, tag)

    if overwrite:
        out = path
    else:
        out = path.replace(".enc", ".dec")
    
    open(out, "wb").write(plain)
    return out


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    # Generar claves RSA y guardarlas en archivos PEM
    priv, pub = gen_rsa_keys()

    priv_pem = pem_private(priv)
    pub_pem = pem_public(pub)

    open("private_key.pem", "w").write(priv_pem)
    open("public_key.pem", "w").write(pub_pem)
    print("Claves RSA generadas y guardadas en 'private_key.pem' y 'public_key.pem'.")

    # pedir argumento opcional de archivo a encriptar
    import sys

    if len(sys.argv) > 1:
        file_to_encrypt = sys.argv[1]
        print(f"Encriptando archivo: {file_to_encrypt}")
        enc = encrypt_file(file_to_encrypt, pub_pem, overwrite=True)
        print("encrypted:", enc)

        dec = decrypt_file(enc, priv_pem, overwrite=True)
        print("decrypted:", dec)
    else:
        print("Para encriptar un archivo, ejecute: python rsa_crypto.py <archivo>")