from cryptography.fernet import Fernet

# Load the secret key securely
SECRET_KEY = 'a3HoyA5LkOzLvbysWaVtKi_aTR0F2BNrpLNaartz648='

# Create an instance of the Fernet cipher
cipher_suite = Fernet(SECRET_KEY)

def encrypt_data(data):
    if isinstance(data, str):
        # If data is a string, encode it to bytes before encrypting
        data = data.encode()
    encrypted_data = cipher_suite.encrypt(data)
    return encrypted_data

def decrypt_data(encrypted_data):
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
    return decrypted_data