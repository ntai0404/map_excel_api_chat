import hashlib
import base64

def generate_code_challenge(verifier):
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    b64 = base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')
    return b64

verifier = "MSmzMLI8bYfrbRfZID1XeHdirWkK8FyxC2e6U6sE3kR"
challenge_log = "Z9zCXcjWLSq_Z05SOLQKdU1xEYZn6lBwSK9TWpXWoIA"

calculated = generate_code_challenge(verifier)

print(f"Verifier: {verifier}")
print(f"Expected Challenge (from log): {challenge_log}")
print(f"Calculated Challenge:          {calculated}")
print(f"Match: {challenge_log == calculated}")
