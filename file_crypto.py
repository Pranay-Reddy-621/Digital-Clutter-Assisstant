from cryptography.fernet import Fernet
import os
import argparse

def generate_key(key_path='encryption_key.key'):
    """Generate and save encryption key"""
    if os.path.exists(key_path):
        raise FileExistsError("Encryption key already exists. Delete it first to generate a new one.")
    
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f: 
        f.write(key)
    print(f"[✓] Encryption key generated at {os.path.abspath(key_path)}")
    return key

def load_key(key_path='encryption_key.key'):
    """Load encryption key from file"""
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Encryption key not found at {key_path}")
    
    with open(key_path, 'rb') as f:
        return f.read()

def encrypt_file(input_path, key=None, output_path=None):
    """Encrypt a file with optional custom output path"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not key:
        key = load_key()
    
    fernet = Fernet(key)
    
    with open(input_path, 'rb') as f:
        file_data = f.read()
    
    encrypted_data = fernet.encrypt(file_data)
    output_path = output_path or f"{input_path}.encrypted"
    
    with open(output_path, 'wb') as f:
        f.write(encrypted_data)
    
    print(f"[✓] Encrypted {input_path} -> {output_path}")
    return output_path

def decrypt_file(input_path, key=None, output_path=None):
    """Decrypt a file with optional custom output path"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not key:
        key = load_key()
    
    fernet = Fernet(key)
    
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()
    
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except:
        raise ValueError("Invalid key or corrupted file")
    
    output_path = output_path or input_path.replace('.encrypted', '')
    
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)
    
    print(f"[✓] Decrypted {input_path} -> {output_path}")
    return output_path

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="File encryption/decryption tool")
    subparsers = parser.add_subparsers(dest='command')

    # Generate key command
    gen_parser = subparsers.add_parser('genkey', help='Generate new encryption key')

    # Encrypt command
    enc_parser = subparsers.add_parser('encrypt', help='Encrypt a file')
    enc_parser.add_argument('input', help='File to encrypt')
    enc_parser.add_argument('-o', '--output', help='Output path')

    # Decrypt command
    dec_parser = subparsers.add_parser('decrypt', help='Decrypt a file')
    dec_parser.add_argument('input', help='File to decrypt')
    dec_parser.add_argument('-o', '--output', help='Output path')

    args = parser.parse_args()

    try:
        if args.command == 'genkey':
            generate_key()
        elif args.command == 'encrypt':
            encrypt_file(args.input, output_path=args.output)
        elif args.command == 'decrypt':
            decrypt_file(args.input, output_path=args.output)
        else:
            parser.print_help()
    except Exception as e:
        print(f"[x] Error: {str(e)}")

if __name__ == "__main__":
    main()

