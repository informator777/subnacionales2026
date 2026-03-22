import bcrypt

# 1. Lista de contraseñas que quieres hashear
passwords = ['admin', 'registrador1']

print("\n" + "="*50)
print("🔑 GENERADOR DE HASHES (MÉTODO DIRECTO BCRYPT)")
print("="*50)

for p in passwords:
    # Generar el hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(p.encode('utf-8'), salt)
    
    print(f"\nCONTRASEÑA: {p}")
    print(f"HASH PARA APP.PY: {hashed.decode('utf-8')}")
    print("-" * 50)

print("\nCopia el hash (incluyendo el $2b$...) y pégalo en tu config.")
