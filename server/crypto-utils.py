from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Generate server key once
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

def get_public_key_bytes():
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def derive_key(client_pub_bytes):
    client_pub = serialization.load_pem_public_key(client_pub_bytes)

    shared_key = private_key.exchange(ec.ECDH(), client_pub)

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'iot-auth'
    ).derive(shared_key)

def decrypt(key, iv, ciphertext):
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()