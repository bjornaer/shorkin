# Shorkin

A quantum cryptography toolkit for Python. Implements **Shor's algorithm** for integer factorization and **Quantum Key Distribution (QKD)** protocols with HTTP and gRPC transport integrations.

Quantum simulation is powered by [Google Cirq](https://quantumai.google/cirq). QKD-derived keys are used for AES-256-GCM payload encryption.

## Installation

```bash
# Core library (Shor's algorithm + QKD protocols)
pip install shorkin

# With a specific web framework
pip install shorkin[fastapi]
pip install shorkin[django]
pip install shorkin[starlette]
pip install shorkin[tornado]

# With gRPC support
pip install shorkin[grpc]

# Everything
pip install shorkin[all]
```

Requires Python 3.10+.

## Shor's Algorithm

Factor composite integers using a quantum (simulated via Cirq) or classical order-finding backend.

### CLI

```bash
# Factor an integer
shorkin factor 15
# 15 = 3 x 5

# Factor with a specific mode
shorkin factor 21 --mode classical
shorkin factor 15 --mode quantum --verbose

# Factor the modulus from an RSA public key
shorkin factor-key path/to/public.pem
```

### Library

```python
from shorkin.factor import factor
from shorkin.classical.order_finder import find_order

class ClassicalFinder:
    method_name = "classical"
    def find_order(self, x, n):
        return find_order(x, n)

result = factor(15, ClassicalFinder())
print(result.factors)  # [3, 5]
```

## QKD Protocols

Three quantum key distribution protocols, all following a common `QKDProtocol` interface:

| Protocol | Description | Sifting Yield | QBER Threshold |
|----------|-------------|---------------|----------------|
| **BB84** | 2 bases, 4 states (Bennett-Brassard 1984) | ~50% | ~11% |
| **B92**  | 2 non-orthogonal states (Bennett 1992) | ~25% | ~5% |
| **E91**  | Entanglement-based with CHSH Bell test (Ekert 1991) | ~22% | ~11% |

### Basic Usage

```python
from shorkin.qkd import BB84, B92, E91, SimulatedChannel

# Create a simulated quantum channel
channel = SimulatedChannel(error_rate=0.02, seed=42)

# Generate a shared key using BB84
protocol = BB84(seed=42)
result = protocol.generate_key(num_qubits=4096, channel=channel)

print(f"Protocol:  {result.protocol}")
print(f"QBER:      {result.qber:.4f}")
print(f"Key:       {result.final_key.hex()}")
print(f"Key bits:  {result.key_length_bits}")
```

### Choosing a Protocol

```python
# BB84 -- the standard, good balance of efficiency and security
protocol = BB84(seed=42)
result = protocol.generate_key(num_qubits=4096, channel=channel)

# B92 -- simpler (2 states), lower yield, needs more qubits
protocol = B92(seed=42)
result = protocol.generate_key(num_qubits=8000, channel=channel)

# E91 -- entanglement-based, includes Bell inequality (CHSH) test
protocol = E91(seed=42)
result = protocol.generate_key(num_qubits=20000, channel=channel)
print(f"CHSH value: {result.metadata['chsh_value']:.3f}")  # > 2.0 = secure
```

### Encrypt / Decrypt with QKD Keys

```python
from shorkin.qkd import BB84, SimulatedChannel, encrypt, decrypt

channel = SimulatedChannel(seed=42)
result = BB84(seed=42).generate_key(num_qubits=4096, channel=channel)

ciphertext = encrypt(b"secret payload", result.final_key)
plaintext = decrypt(ciphertext, result.final_key)
assert plaintext == b"secret payload"
```

### Simulated Channel Options

```python
from shorkin.qkd import SimulatedChannel

# Perfect channel (no errors, no loss)
channel = SimulatedChannel()

# Noisy channel (5% bit-flip error rate)
channel = SimulatedChannel(error_rate=0.05)

# Lossy channel (10% photon loss)
channel = SimulatedChannel(loss_rate=0.10)

# Both noise and loss
channel = SimulatedChannel(error_rate=0.03, loss_rate=0.05, seed=42)
```

The `QuantumChannel` is a `typing.Protocol` -- you can implement your own to connect to real quantum hardware.

## HTTP Integration

QKD key exchange runs at `/.well-known/qkd/initiate`. Once a session is established, request and response bodies are AES-256-GCM encrypted using the QKD-derived key, identified by the `X-QKD-Session-Id` header.

### FastAPI

```python
from fastapi import Depends, FastAPI
from shorkin.transport.http.fastapi import QKDMiddleware, QKDSession, qkd_session

app = FastAPI()

# Option 1: Middleware (encrypts all responses for active sessions)
app.add_middleware(QKDMiddleware, protocol="bb84")

# Option 2: Dependency injection (per-route control)
@app.get("/secure")
async def secure_endpoint(qkd: QKDSession = Depends(qkd_session("bb84"))):
    if qkd.is_active:
        return {"encrypted": qkd.encrypt(b"secret").hex()}
    return {"message": "no QKD session"}
```

#### Client usage with FastAPI

```python
import httpx

# Step 1: Initiate key exchange
resp = httpx.post("http://localhost:8000/.well-known/qkd/initiate", json={
    "protocol": "bb84",
    "peer_id": "my-client",
})
session_id = resp.json()["session_id"]

# Step 2: Make requests with the session
resp = httpx.get("http://localhost:8000/secure", headers={
    "X-QKD-Session-Id": session_id,
})
# Response body is AES-256-GCM encrypted
```

### Starlette

```python
from starlette.applications import Starlette
from shorkin.transport.http.starlette import QKDMiddleware

app = Starlette(routes=[...])
app.add_middleware(QKDMiddleware, protocol="bb84")
```

### Django

```python
# settings.py
MIDDLEWARE = [
    # ...
    "shorkin.transport.http.django.QKDMiddleware",
]

SHORKIN_QKD = {
    "PROTOCOL": "bb84",      # or "b92", "e91"
    "NUM_QUBITS": 4096,
    "TARGET_KEY_BITS": 256,
    "STRICT": False,          # True = reject requests without QKD session
}
```

### Tornado

```python
import tornado.web
from shorkin.transport.http.tornado import QKDRequestMixin, qkd_routes

class SecureHandler(QKDRequestMixin, tornado.web.RequestHandler):
    def get(self):
        self.write(b"encrypted if QKD session is active")

app = tornado.web.Application(
    qkd_routes("bb84") + [
        (r"/secure", SecureHandler, {"qkd_protocol": "bb84"}),
    ]
)
```

### Strict Mode

All HTTP integrations support `strict=True`, which rejects any request without an active QKD session (returns 403). QKD negotiation endpoints are always accessible.

## gRPC Integration

QKD key exchange is exposed as a `QKDKeyExchange` gRPC service. Client and server interceptors handle session metadata transparently.

### Server

```python
from concurrent import futures
import grpc
from shorkin.transport.grpc.servicer import QKDKeyExchangeServicer
from shorkin.transport.grpc.interceptor import QKDServerInterceptor
from shorkin.transport.grpc import qkd_pb2_grpc

interceptor = QKDServerInterceptor(protocol="bb84")
server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[interceptor],
)
servicer = QKDKeyExchangeServicer(protocol="bb84")
qkd_pb2_grpc.add_QKDKeyExchangeServicer_to_server(servicer, server)
server.add_insecure_port("[::]:50051")
server.start()
server.wait_for_termination()
```

### Client

```python
import grpc
from shorkin.transport.grpc.interceptor import QKDClientInterceptor
from shorkin.transport.grpc import qkd_pb2, qkd_pb2_grpc

# Set up intercepted channel
interceptor = QKDClientInterceptor(protocol="bb84")
channel = grpc.intercept_channel(
    grpc.insecure_channel("localhost:50051"),
    interceptor,
)
stub = qkd_pb2_grpc.QKDKeyExchangeStub(channel)

# Initiate key exchange
response = stub.Initiate(qkd_pb2.KeyExchangeInitRequest(
    protocol="bb84",
    peer_id="my-service",
))
print(f"Session: {response.session_id}")
print(f"Status:  {response.status}")

# Set session for subsequent calls
interceptor.session_id = response.session_id
```

## Architecture

### QKD and Classical Networks

True QKD requires a physical quantum channel (photon transmission over fiber optics). This library simulates the quantum channel using Cirq, making it suitable for:

- **Education and prototyping** -- learn and develop QKD-secured applications without quantum hardware
- **Integration testing** -- validate your application's encryption pipeline end-to-end
- **Research** -- experiment with protocol parameters, noise models, and error thresholds

The classical post-processing (basis reconciliation, error estimation, privacy amplification) runs over standard HTTP/gRPC and is protocol-accurate. The `QuantumChannel` abstraction is pluggable -- swap `SimulatedChannel` for a real hardware adapter without changing application code.

### Package Structure

```
shorkin/
    classical/          # Classical order finding (brute-force)
    quantum/            # Quantum order finding (Cirq QPE)
    factor.py           # Shor's algorithm orchestration
    cli.py              # CLI entry point
    qkd/                # QKD protocol engines
        bb84.py         # BB84 protocol
        b92.py          # B92 protocol
        e91.py          # E91 protocol
        channel.py      # QuantumChannel Protocol + SimulatedChannel
        encryption.py   # AES-256-GCM encrypt/decrypt
        key_store.py    # Session key storage with rotation/expiration
    transport/          # HTTP & gRPC integrations
        http/
            fastapi.py  # FastAPI middleware + Depends()
            starlette.py
            django.py
            tornado.py
        grpc/
            servicer.py     # QKDKeyExchange gRPC service
            interceptor.py  # Client + server interceptors
```

### Key Types

```python
from shorkin.qkd import QKDResult

result: QKDResult
result.final_key          # bytes -- the usable symmetric key
result.raw_key            # bytes -- key before privacy amplification
result.protocol           # str -- "bb84", "b92", or "e91"
result.qber               # float -- quantum bit error rate
result.key_length_bits    # int -- final key length in bits
result.initial_qubit_count  # int -- qubits transmitted
result.sifted_key_length  # int -- bits after sifting
result.amplified          # bool -- privacy amplification applied
result.metadata           # dict -- protocol-specific (e.g., chsh_value for E91)
```

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/yourusername/shorkin.git
cd shorkin
pip install -e ".[all]"

# Run tests
pytest

# Run only QKD tests
pytest tests/qkd/

# Run only transport tests
pytest tests/transport/

# Run only the original Shor tests
pytest tests/test_*.py
```

## License

MIT
