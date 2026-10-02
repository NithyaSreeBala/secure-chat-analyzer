"""
encryption.py
-------------
Handles at-rest encryption of chat messages using Fernet
(AES-128 in CBC mode + HMAC for integrity, from the `cryptography` library).

Every message is encrypted BEFORE it is written to the database, and
decrypted only when it needs to be shown to an authorized, authenticated
user. This means that even if the database file is stolen, raw chat
content is not readable without the ENCRYPTION_KEY.
"""

from cryptography.fernet import Fernet, InvalidToken


class MessageEncryptor:
    def __init__(self, key: str):
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY is missing. Generate one with:\n"
                "python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\"\n"
                "and add it to backend/.env as ENCRYPTION_KEY=<value>"
            )
        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string, return a base64 token (str) safe for DB storage."""
        token = self.fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Decrypt a stored token back into the original plaintext string."""
        try:
            plaintext = self.fernet.decrypt(token.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken:
            return "[DECRYPTION FAILED - message may be corrupted]"


if __name__ == "__main__":
    # Quick manual test: generate a key and round-trip a message.
    key = Fernet.generate_key().decode()
    enc = MessageEncryptor(key)
    token = enc.encrypt("hello world, this is a secret")
    print("Encrypted:", token)
    print("Decrypted:", enc.decrypt(token))
