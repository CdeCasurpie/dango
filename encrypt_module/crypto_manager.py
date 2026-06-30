import os
import json
import secrets
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

CHUNK_SIZE = 64 * 1024  # 64KB para no saturar RAM

def log(message, echo=True, end="\n"):
    """Función unificada para imprimir logs de debug si echo es True"""
    if echo:
        print(message, end=end)

def generate_key():
    return secrets.token_hex(32)

def encrypt_file_stream(source_path, dest_path, key_hex):
    key = bytes.fromhex(key_hex)
    nonce = secrets.token_bytes(12)
    
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    
    with open(source_path, 'rb') as fin, open(dest_path, 'wb') as fout:
        fout.write(nonce)
        while True:
            chunk = fin.read(CHUNK_SIZE)
            if not chunk:
                break
            encrypted_chunk = encryptor.update(chunk)
            fout.write(encrypted_chunk)
        
        encryptor.finalize()
        fout.write(encryptor.tag)
    
    return True

def decrypt_file_stream(encrypted_path, dest_path, key_hex):
    key = bytes.fromhex(key_hex)
    file_size = os.path.getsize(encrypted_path)
    
    if file_size < 28:
        raise ValueError(f"Archivo demasiado pequeño: {file_size} bytes")
        
    with open(encrypted_path, 'rb') as fin, open(dest_path, 'wb') as fout:
        nonce = fin.read(12)
        fin.seek(-16, 2)
        tag = fin.read(16)
        fin.seek(12)
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        bytes_to_read = file_size - 28
        
        while bytes_to_read > 0:
            chunk_size = min(CHUNK_SIZE, bytes_to_read)
            chunk = fin.read(chunk_size)
            if not chunk:
                break
            decrypted_chunk = decryptor.update(chunk)
            fout.write(decrypted_chunk)
            bytes_to_read -= len(chunk)
            
        decryptor.finalize()
        
    return True

def verify_json_integrity(json_file, echo=True):
    hash_file = json_file + '.hash'
    if not os.path.exists(hash_file):
        log(f"Advertencia: No se encontró archivo de hash ({hash_file})", echo)
        return False
    
    try:
        with open(hash_file, 'r') as f:
            stored_hash = f.read().strip()
        
        with open(json_file, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        if stored_hash == actual_hash:
            return True
        else:
            log("ERROR: El registro de claves fue modificado.", echo)
            return False
    except Exception as e:
        log(f"Error verificando integridad: {e}", echo)
        return False

def encrypt_all_files(main_path: str, keys_out_name: str, echo=True) -> str:
    """
    Encripta todos los archivos en un directorio y guarda las claves en un archivo JSON.
    Devuelve la ruta del archivo de claves.
    """
    if not os.path.exists(main_path):
        log(f"Directorio objetivo no encontrado: {main_path}", echo)
        return None
        
    files_to_encrypt = []
    # Evitar encriptar el archivo de llaves si cae en el mismo path
    keys_basename = os.path.basename(keys_out_name)
    
    for root, dirs, files in os.walk(main_path):
        for file in files:
            if file == keys_basename or file == f"{keys_basename}.hash":
                continue
            file_path = os.path.join(root, file)
            if not file_path.endswith('.encrypted'):
                files_to_encrypt.append(file_path)
                
    total = len(files_to_encrypt)
    if total == 0:
        log("No se encontraron archivos para encriptar.", echo)
        return None
        
    log(f"Encontrados {total} archivos para encriptar en '{main_path}'.", echo)
    registry = {}
    
    for i, file_path in enumerate(files_to_encrypt, 1):
        try:
            key = generate_key()
            encrypted_path = file_path + '.encrypted'
            
            encrypt_file_stream(file_path, encrypted_path, key)
            
            registry[file_path] = {
                "key": key,
                "encrypted_path": encrypted_path
            }
            
            os.remove(file_path)
            
            progress = int(30 * i / total)
            bar = "[" + "#" * progress + "." * (30 - progress) + "]"
            log(f"\r{bar} {i}/{total}", echo, end="")
            
        except Exception as e:
            log(f"\nError en {file_path}: {e}", echo)
    
    log("", echo) # Salto de linea final
    
    # Asegurar que retornamos una ruta absoluta
    keys_abs_path = os.path.abspath(keys_out_name)
    
    # Guardar JSON
    with open(keys_abs_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)
        
    # Calcular y guardar hash SHA-256
    with open(keys_abs_path, 'rb') as f:
        json_hash = hashlib.sha256(f.read()).hexdigest()
        
    with open(f"{keys_abs_path}.hash", 'w') as f:
        f.write(json_hash)
        
    log(f"Registro guardado: {keys_abs_path}", echo)
    log(f"Hash de integridad: {keys_abs_path}.hash", echo)
    
    return keys_abs_path

def decrypt_all_files(main_path: str, keys_path: str, echo=True) -> bool:
    """
    Desencripta todos los archivos en un directorio usando un archivo JSON de llaves.
    Devuelve True si la operación fue exitosa, False en caso de error.
    """
    if not os.path.exists(keys_path):
        log(f"No se encontró el archivo de llaves: {keys_path}", echo)
        return False
        
    if not verify_json_integrity(keys_path, echo):
        log("Integridad comprometida. Abortando desencriptación.", echo)
        return False
        
    with open(keys_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
        
    total = len(registry)
    success = 0
    failed = 0
    
    log(f"Desencriptando {total} archivos...", echo)
    
    for i, (original_path, metadata) in enumerate(registry.items(), 1):
        try:
            enc_path = metadata["encrypted_path"]
            key = metadata["key"]
            
            if not os.path.exists(enc_path):
                log(f"\nNo encontrado: {enc_path}", echo)
                failed += 1
                continue
                
            decrypt_file_stream(enc_path, original_path, key)
            os.remove(enc_path)
            
            success += 1
            
            progress = int(30 * i / total)
            bar = "[" + "#" * progress + "." * (30 - progress) + "]"
            log(f"\r{bar} {i}/{total}", echo, end="")
            
        except Exception as e:
            log(f"\nError en {original_path}: {e}", echo)
            failed += 1
            
    log("", echo) # Salto de linea final
    log(f"Completado. Exitosos: {success}, Fallidos: {failed}", echo)
    
    return True