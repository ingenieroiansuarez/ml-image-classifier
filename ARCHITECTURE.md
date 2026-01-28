# ML Image Classifier - Arquitectura Técnica Detallada

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Tech Stack Completo](#tech-stack-completo)
5. [Flujos de Datos](#flujos-de-datos)
6. [Base de Datos](#base-de-datos)
7. [APIs y Contratos](#apis-y-contratos)
8. [Patrones de Diseño](#patrones-de-diseño)
9. [Deployment y Containerización](#deployment-y-containerización)
10. [Escalabilidad y Performance](#escalabilidad-y-performance)

---

## Visión General

Este proyecto implementa un **sistema de clasificación de imágenes basado en Machine Learning** utilizando una arquitectura de microservicios. El sistema puede clasificar imágenes en más de 1000 categorías diferentes usando un modelo de CNN (Convolutional Neural Network) pre-entrenado ResNet50 de ImageNet.

### Características Principales
- **Arquitectura de Microservicios**: Componentes desacoplados que se comunican a través de Redis
- **Procesamiento Asíncrono**: Cola de trabajos para manejar predicciones ML de forma no-bloqueante
- **Autenticación JWT**: Sistema de seguridad basado en tokens para proteger endpoints
- **Escalabilidad Horizontal**: Capacidad de escalar workers ML independientemente
- **Containerización Completa**: Todos los servicios corriendo en Docker
- **Testing Exhaustivo**: Tests unitarios, de integración y de estrés

---

## Arquitectura del Sistema

### Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Browser)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UI LAYER (Streamlit)                        │
│  - Puerto: 9090                                                  │
│  - Funciones: Login, Upload Images, Display Results, Feedback   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ REST API (Port 8000)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                           │
│  - Puerto: 8000 (interno 5000)                                  │
│  - Endpoints: /login, /users, /model/predict, /feedback         │
│  - Autenticación: JWT Bearer Token                              │
│  - Validación: Pydantic Schemas                                 │
└─────┬──────────────────────┬──────────────────────┬─────────────┘
      │                      │                      │
      │                      │                      │
      ▼                      ▼                      ▼
┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│ PostgreSQL  │    │   Redis Queue    │    │  File System │
│   (DB)      │    │   (Message Broker)│    │  (Uploads)   │
│             │    │                  │    │              │
│ - Users     │    │ - Job Queue      │    │ - Images     │
│ - Feedback  │    │ - Results Cache  │    │   (MD5 hash) │
└─────────────┘    └────────┬─────────┘    └──────────────┘
                            │
                            │ BRPOP/LPUSH
                            ▼
                   ┌─────────────────┐
                   │  ML SERVICE     │ (Scalable: 1-N instances)
                   │  (Worker Pool)  │
                   │                 │
                   │ - ResNet50 CNN  │
                   │ - TensorFlow    │
                   │ - Image         │
                   │   Preprocessing │
                   └─────────────────┘
```

### Flujo de Comunicación

1. **Cliente → UI**: Usuario interactúa con interfaz web (Streamlit)
2. **UI → API**: Peticiones HTTP/REST con JWT token
3. **API → DB**: Operaciones CRUD (usuarios, feedback)
4. **API → Redis**: Encola trabajos de predicción (LPUSH)
5. **ML Service → Redis**: Consume trabajos (BRPOP), procesa, devuelve resultados (SET)
6. **API → Redis**: Polling para obtener resultados (GET)
7. **API → UI**: Retorna resultados JSON
8. **UI → Cliente**: Muestra predicción al usuario

---

## Componentes Principales

### 1. API Service (FastAPI)

**Ubicación**: `./api/`

**Responsabilidades**:
- Autenticación y autorización de usuarios
- Gestión de uploads de imágenes
- Validación de inputs
- Encolado de trabajos ML
- Polling de resultados
- Persistencia de feedback

**Estructura Interna**:
```
api/
├── main.py                 # Punto de entrada, configuración FastAPI
├── Dockerfile             # Multi-stage build (test, build)
├── requirements.txt       # Dependencias Python
├── populate_db.py        # Script de inicialización DB
│
├── app/
│   ├── settings.py       # Configuración (env vars)
│   ├── db.py            # Database engine y session
│   ├── utils.py         # Funciones utilidad (hash, validación)
│   │
│   ├── auth/            # Módulo de autenticación
│   │   ├── jwt.py       # Generación/validación tokens JWT
│   │   ├── router.py    # Endpoint /login
│   │   └── schema.py    # Pydantic models (LoginRequest, Token)
│   │
│   ├── user/            # Módulo de usuarios
│   │   ├── models.py    # SQLAlchemy model (User)
│   │   ├── router.py    # Endpoints CRUD usuarios
│   │   ├── services.py  # Lógica de negocio
│   │   ├── schema.py    # Pydantic schemas (UserCreate, UserResponse)
│   │   ├── hashing.py   # Bcrypt para passwords
│   │   └── validator.py # Validaciones custom
│   │
│   ├── model/           # Módulo de predicción ML
│   │   ├── router.py    # POST /model/predict
│   │   ├── services.py  # Redis queue management
│   │   └── schema.py    # Pydantic schemas (PredictResponse)
│   │
│   └── feedback/        # Módulo de feedback
│       ├── models.py    # SQLAlchemy model (Feedback)
│       ├── router.py    # POST /feedback, GET /feedback
│       ├── services.py  # Lógica de negocio
│       └── schema.py    # Pydantic schemas
│
└── tests/               # Tests unitarios
    ├── test_router_user.py
    ├── test_router_model.py
    ├── test_router_feedback.py
    └── test_utils.py
```

**Endpoints Principales**:

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| POST | `/login` | No | Autenticación con credenciales, retorna JWT |
| POST | `/users` | No | Registro de nuevo usuario |
| GET | `/users/{id}` | Sí | Obtener información de usuario |
| POST | `/model/predict` | Sí | Upload imagen para clasificación |
| POST | `/feedback` | Sí | Enviar feedback sobre predicción |
| GET | `/feedback` | Sí | Listar todo el feedback |
| GET | `/docs` | No | Documentación Swagger interactiva |

**Tecnologías**:
- **FastAPI 0.78.0**: Framework web async
- **Uvicorn + Gunicorn**: ASGI server para producción
- **SQLAlchemy 1.4.39**: ORM para PostgreSQL
- **Pydantic**: Validación de datos y serialización
- **python-jose**: JWT encoding/decoding
- **passlib + bcrypt**: Hashing de passwords
- **redis-py**: Cliente Redis para Python
- **python-multipart**: Manejo de uploads

**Configuración (Environment Variables)**:
```bash
POSTGRES_DB=sp3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_HOST=db
SECRET_KEY=secret_key_for_jwt
REDIS_IP=redis
REDIS_PORT=6379
```

---

### 2. ML Service (TensorFlow + ResNet50)

**Ubicación**: `./model/`

**Responsabilidades**:
- Cargar modelo ResNet50 pre-entrenado (ImageNet)
- Escuchar cola Redis para nuevos trabajos
- Preprocesar imágenes (resize, normalize)
- Ejecutar inferencia del modelo
- Retornar predicción + confidence score a Redis

**Estructura**:
```
model/
├── ml_service.py          # Worker principal
├── settings.py            # Configuración Redis
├── requirements.txt       # TensorFlow 2.8.0, keras, etc.
├── Dockerfile            # Build con TensorFlow
├── Dockerfile.M1         # Build optimizado para Mac M1
└── tests/
    └── test_model.py     # Test de inferencia
```

**Funcionamiento Interno** (`ml_service.py`):

```python
# 1. Inicialización
redis_client = redis.Redis(host=REDIS_IP, port=6379, db=0)
model = ResNet50(weights='imagenet')  # ~100MB download

# 2. Loop infinito de procesamiento
while True:
    # Bloqueo esperando trabajo (BRPOP)
    job = redis_client.brpop('job_queue', timeout=5)
    
    if job:
        job_id, image_path = parse_job(job)
        
        # 3. Cargar y preprocesar imagen
        img = image.load_img(image_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        
        # 4. Inferencia
        predictions = model.predict(img_array)
        decoded = decode_predictions(predictions, top=1)[0][0]
        
        # 5. Guardar resultado en Redis
        result = {
            'success': True,
            'prediction': decoded[1],  # Clase
            'score': float(decoded[2])  # Confidence
        }
        redis_client.set(f'result:{job_id}', json.dumps(result))
```

**Modelo ResNet50**:
- **Arquitectura**: 50 capas profundas con conexiones residuales
- **Tamaño**: ~100 MB de pesos
- **Input**: Imágenes RGB 224x224 pixels
- **Output**: Vector de 1000 probabilidades (ImageNet classes)
- **Preprocessing**: Normalización según ImageNet stats
  - Mean RGB: [103.939, 116.779, 123.68]
  - Modo: caffe (BGR ordering)

**Categorías de Clasificación** (ejemplos de 1000+ clases):
- Animales: Eskimo_dog, Persian_cat, tiger, etc.
- Vehículos: sports_car, airliner, ambulance, etc.
- Objetos: laptop, coffee_mug, basketball, etc.
- Alimentos: pizza, strawberry, chocolate_sauce, etc.

**Escalabilidad**:
```bash
# Escalar a 3 workers
docker-compose up -d --scale model=3

# Cada instancia:
# - Carga su propia copia del modelo en memoria (~100MB RAM)
# - Consume de la misma cola Redis (balanceo automático)
# - Procesa trabajos en paralelo
```

---

### 3. UI Service (Streamlit)

**Ubicación**: `./ui/`

**Responsabilidades**:
- Interfaz gráfica para usuarios finales
- Formulario de login
- Upload de imágenes
- Visualización de resultados
- Envío de feedback

**Estructura**:
```
ui/
├── app/
│   ├── image_classifier_app.py  # Aplicación Streamlit
│   └── settings.py              # API_BASE_URL
├── requirements.txt             # streamlit, requests, Pillow
├── Dockerfile                   # Multi-stage build
└── tests/
    └── test_image_classifier_app.py
```

**Funciones Principales**:

```python
def login(username: str, password: str) -> Optional[str]:
    """Autenticación contra API, retorna JWT token"""
    response = requests.post(f"{API_BASE_URL}/login", 
                           headers={...}, 
                           data={...})
    return response.json()["access_token"] if response.status_code == 200 else None

def predict(token: str, uploaded_file) -> requests.Response:
    """Upload imagen a API para clasificación"""
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{API_BASE_URL}/model/predict", 
                        headers=headers, 
                        files=files)

def send_feedback(token: str, feedback: str, score: float, 
                  prediction: str, image_file_name: str) -> requests.Response:
    """Enviar feedback sobre predicción"""
    data = {
        "feedback": feedback,
        "score": score,
        "predicted_class": prediction,
        "image_file_name": image_file_name
    }
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{API_BASE_URL}/feedback", 
                        headers=headers, 
                        json=data)
```

**Interfaz de Usuario**:
1. **Página Login**:
   - Campos: Email, Password
   - Validación en cliente
   - Almacena token en session_state

2. **Página Principal** (post-login):
   - File uploader (jpg, jpeg, png, gif)
   - Preview de imagen
   - Botón "Classify"
   - Display de resultado con confidence %
   - Campo de feedback opcional
   - Logout button

**Tecnologías**:
- **Streamlit 1.9.0**: Framework de UI para Python
- **Pillow (PIL)**: Procesamiento de imágenes
- **requests**: Cliente HTTP

---

### 4. Database Service (PostgreSQL)

**Imagen Docker**: `postgres:13-alpine`

**Configuración**:
```yaml
ports:
  - "5433:5432"  # Mapeo externo:interno
volumes:
  - postgres_data:/var/lib/postgresql/data
environment:
  POSTGRES_DB: sp3
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 5s
  timeout: 5s
  retries: 5
```

**Schema de Base de Datos**:

```sql
-- Tabla de Usuarios
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Bcrypt hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Feedback
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    feedback TEXT NOT NULL,
    score FLOAT NOT NULL,             -- Confidence del modelo
    predicted_class VARCHAR(255) NOT NULL,
    image_file_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_created_at ON feedback(created_at);
```

**Modelos SQLAlchemy**:

```python
# User Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # Hashed
    feedbacks = relationship("Feedback", back_populates="user")

# Feedback Model
class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    feedback = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    predicted_class = Column(String, nullable=False)
    image_file_name = Column(String, nullable=False)
    user = relationship("User", back_populates="feedbacks")
```

**Inicialización** (`populate_db.py`):
```python
# 1. Drop all tables
Base.metadata.drop_all(bind=engine)

# 2. Create all tables
Base.metadata.create_all(bind=engine)

# 3. Create default admin user
admin = User(
    email="admin@example.com",
    username="admin",
    password=bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
)
db.add(admin)
db.commit()
```

---

### 5. Message Broker (Redis)

**Imagen Docker**: `redis:6.2.6`

**Propósito**:
- **Job Queue**: Cola FIFO para trabajos de predicción
- **Results Cache**: Almacenamiento temporal de resultados
- **Comunicación Async**: Desacopla API de ML workers

**Estructuras de Datos Usadas**:

```python
# 1. Job Queue (List)
# API enqueue trabajo
redis.lpush('job_queue', json.dumps({
    'job_id': 'uuid-123',
    'image_path': '/src/uploads/abc123.jpg'
}))

# ML Worker consume trabajo (blocking)
job = redis.brpop('job_queue', timeout=5)

# 2. Results Cache (String con TTL)
# ML Worker guarda resultado
redis.set(
    f'result:{job_id}', 
    json.dumps({
        'success': True,
        'prediction': 'Eskimo_dog',
        'score': 0.9346
    }),
    ex=300  # TTL 5 minutos
)

# API polling resultado
result = redis.get(f'result:{job_id}')
```

**Ventajas del Patrón**:
- ✅ **Desacoplamiento**: API no necesita conocer workers
- ✅ **Escalabilidad**: Múltiples workers compiten por trabajos
- ✅ **Resiliencia**: Si worker falla, otro toma el trabajo
- ✅ **Performance**: API no bloquea esperando ML
- ✅ **Balanceo de Carga**: Automático por naturaleza de BRPOP

---

## Tech Stack Completo

### Backend Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Python | 3.8.13 | Lenguaje principal |
| FastAPI | 0.78.0 | Framework web async |
| Uvicorn | 0.18.2 | ASGI server |
| Gunicorn | 20.1.0 | Process manager |
| SQLAlchemy | 1.4.39 | ORM para PostgreSQL |
| Pydantic | 1.9.1 | Validación de datos |
| PostgreSQL | 13-alpine | Base de datos relacional |
| Redis | 6.2.6 | Message broker & cache |

### Machine Learning Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| TensorFlow | 2.8.0 | Framework ML |
| Keras | Incluido en TF | High-level API |
| ResNet50 | ImageNet weights | Modelo CNN pre-entrenado |
| NumPy | 1.22.4 | Arrays numéricos |
| Pillow (PIL) | 9.1.1 | Procesamiento imágenes |

### Frontend Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Streamlit | 1.9.0 | Framework UI |
| requests | 2.28.1 | Cliente HTTP |
| Pillow | 9.1.1 | Manejo de imágenes |

### Security Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| python-jose | 3.3.0 | JWT encoding/decoding |
| passlib | 1.7.4 | Password hashing |
| bcrypt | 3.2.2 | Algoritmo de hash |

### DevOps Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Docker | 20+ | Containerización |
| docker-compose | 3.2 | Orquestación multi-container |
| pytest | 7.1.2 | Framework de testing |
| Locust | 2.42.6 | Stress testing / Load testing |

### Networking

| Componente | Configuración |
|------------|---------------|
| Docker Network | `shared_network` (bridge) |
| API External Port | 8000 |
| API Internal Port | 5000 |
| UI External Port | 9090 |
| PostgreSQL External Port | 5433 |
| PostgreSQL Internal Port | 5432 |
| Redis Internal Port | 6379 |

---

## Flujos de Datos

### Flujo 1: Autenticación de Usuario

```
┌────────┐      ┌──────┐      ┌─────────┐      ┌──────────┐
│ Client │      │  UI  │      │   API   │      │ Database │
└───┬────┘      └──┬───┘      └────┬────┘      └────┬─────┘
    │              │               │                │
    │ 1. Enter     │               │                │
    │ credentials  │               │                │
    ├─────────────>│               │                │
    │              │ 2. POST       │                │
    │              │ /login        │                │
    │              ├──────────────>│                │
    │              │               │ 3. Query user  │
    │              │               ├───────────────>│
    │              │               │ 4. User data   │
    │              │               │<───────────────┤
    │              │               │                │
    │              │               │ 5. Verify pwd  │
    │              │               │ (bcrypt)       │
    │              │               │                │
    │              │               │ 6. Generate JWT│
    │              │               │ (HS256)        │
    │              │ 7. Token      │                │
    │              │<──────────────┤                │
    │ 8. Display   │               │                │
    │ logged state │               │                │
    │<─────────────┤               │                │
```

**Detalles Técnicos**:
- Password hashing: `bcrypt` con salt (factor 12)
- JWT algorithm: `HS256` (HMAC-SHA256)
- Token payload: `{"sub": email, "exp": timestamp}`
- Token expiration: Configurable (default: 30 minutos)

---

### Flujo 2: Clasificación de Imagen (Completo)

```
┌────────┐  ┌──────┐  ┌─────────┐  ┌───────┐  ┌──────────┐  ┌────────┐
│ Client │  │  UI  │  │   API   │  │ Redis │  │ML Service│  │FileSystem│
└───┬────┘  └──┬───┘  └────┬────┘  └───┬───┘  └────┬─────┘  └────┬───┘
    │           │           │           │           │             │
    │ 1. Upload │           │           │           │             │
    │  image    │           │           │           │             │
    ├──────────>│           │           │           │             │
    │           │ 2. POST   │           │           │             │
    │           │ /predict  │           │           │             │
    │           │ + JWT     │           │           │             │
    │           ├──────────>│           │           │             │
    │           │           │ 3. Verify │           │             │
    │           │           │  JWT      │           │             │
    │           │           │           │           │             │
    │           │           │ 4. Validate           │             │
    │           │           │  file type│           │             │
    │           │           │           │           │             │
    │           │           │ 5. Generate MD5       │             │
    │           │           │  hash     │           │             │
    │           │           │           │           │             │
    │           │           │ 6. Save file          │             │
    │           │           ├───────────────────────┼────────────>│
    │           │           │           │           │             │
    │           │           │ 7. Create job         │             │
    │           │           │  (uuid)   │           │             │
    │           │           │           │           │             │
    │           │           │ 8. LPUSH  │           │             │
    │           │           │  job_queue│           │             │
    │           │           ├──────────>│           │             │
    │           │           │           │           │             │
    │           │           │           │ 9. BRPOP  │             │
    │           │           │           │ (blocking)│             │
    │           │           │           │<──────────┤             │
    │           │           │           │           │             │
    │           │           │           │           │10. Load img │
    │           │           │           │           ├────────────>│
    │           │           │           │           │             │
    │           │           │           │           │11. Resize   │
    │           │           │           │           │   224x224   │
    │           │           │           │           │             │
    │           │           │           │           │12. Normalize│
    │           │           │           │           │             │
    │           │           │           │           │13. Predict  │
    │           │           │           │           │  (ResNet50) │
    │           │           │           │           │             │
    │           │           │           │14. SET    │             │
    │           │           │           │ result:{id}             │
    │           │           │           │<──────────┤             │
    │           │           │           │           │             │
    │           │ [POLLING] │           │           │             │
    │           │           │15. GET    │           │             │
    │           │           │ result:{id}           │             │
    │           │           ├──────────>│           │             │
    │           │           │16. Result │           │             │
    │           │           │<──────────┤           │             │
    │           │           │           │           │             │
    │           │17. JSON   │           │           │             │
    │           │ response  │           │           │             │
    │           │<──────────┤           │           │             │
    │18. Display│           │           │           │             │
    │ prediction│           │           │           │             │
    │<──────────┤           │           │           │             │
```

**Detalles del Polling**:
```python
# En api/app/model/services.py
def model_predict(image_path: str) -> dict:
    job_id = str(uuid4())
    job_data = {'job_id': job_id, 'image_path': image_path}
    
    # Encolar trabajo
    redis_client.lpush('job_queue', json.dumps(job_data))
    
    # Polling (máximo 30 segundos)
    for _ in range(60):  # 60 iteraciones * 0.5s = 30s
        result = redis_client.get(f'result:{job_id}')
        if result:
            return json.loads(result)
        time.sleep(0.5)
    
    raise TimeoutError("ML service timeout")
```

**Tiempos Típicos**:
- Upload + validación: ~50ms
- Encolado Redis: ~5ms
- Procesamiento ML: ~100-200ms
  - Load image: ~10ms
  - Preprocess: ~20ms
  - Model inference: ~80-150ms
- Polling overhead: ~10-50ms
- **Total end-to-end**: ~200-350ms

---

### Flujo 3: Envío de Feedback

```
┌────────┐      ┌──────┐      ┌─────────┐      ┌──────────┐
│ Client │      │  UI  │      │   API   │      │ Database │
└───┬────┘      └──┬───┘      └────┬────┘      └────┬─────┘
    │              │               │                │
    │ 1. Write     │               │                │
    │ feedback     │               │                │
    │ (optional)   │               │                │
    ├─────────────>│               │                │
    │              │ 2. POST       │                │
    │              │ /feedback     │                │
    │              │ + JWT         │                │
    │              ├──────────────>│                │
    │              │               │ 3. Verify JWT  │
    │              │               │                │
    │              │               │ 4. Extract     │
    │              │               │ user_id        │
    │              │               │                │
    │              │               │ 5. INSERT INTO │
    │              │               │ feedback       │
    │              │               ├───────────────>│
    │              │               │ 6. OK          │
    │              │               │<───────────────┤
    │              │ 7. 201 Created│                │
    │              │<──────────────┤                │
    │ 8. Success   │               │                │
    │ message      │               │                │
    │<─────────────┤               │                │
```

---

## Patrones de Diseño

### 1. Microservices Architecture
**Patrón**: Descomposición en servicios independientes
- **API Service**: Business logic & orchestration
- **ML Service**: Compute-intensive workload
- **UI Service**: User presentation layer
- **Database**: Data persistence
- **Redis**: Messaging & coordination

**Ventajas**:
- Escalabilidad independiente de cada servicio
- Desarrollo y deployment independientes
- Tecnologías optimizadas por servicio
- Fallos aislados (no cascading failures)

---

### 2. Producer-Consumer Pattern (Job Queue)
**Patrón**: Cola de trabajos asíncrona con Redis
- **Producer**: API encola trabajos (LPUSH)
- **Queue**: Redis List estructura FIFO
- **Consumers**: ML workers compiten por trabajos (BRPOP)

**Implementación**:
```python
# Producer (API)
class ModelService:
    def enqueue_prediction(self, image_path: str) -> str:
        job_id = str(uuid4())
        job = {'job_id': job_id, 'image_path': image_path}
        self.redis.lpush('job_queue', json.dumps(job))
        return job_id

# Consumer (ML Service)
class MLWorker:
    def process_jobs(self):
        while True:
            job = self.redis.brpop('job_queue', timeout=5)
            if job:
                self.predict_and_store(job)
```

**Ventajas**:
- No bloqueo de API
- Balanceo automático de carga
- Escalabilidad horizontal
- Retry automático si worker falla

---

### 3. Repository Pattern
**Patrón**: Abstracción de acceso a datos
```python
# Repositorio genérico
class BaseRepository:
    def __init__(self, model):
        self.model = model
    
    def get_all(self, db: Session):
        return db.query(self.model).all()
    
    def get_by_id(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()
    
    def create(self, db: Session, obj_in: BaseModel):
        db_obj = self.model(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

# Uso específico
class UserRepository(BaseRepository):
    def get_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.email == email).first()
```

---

### 4. Dependency Injection (FastAPI)
**Patrón**: Inyección de dependencias para testing
```python
# Dependencia de database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependencia de autenticación
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    # ... validación
    return email

# Uso en endpoints
@router.post("/feedback")
def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # db y current_user son inyectados automáticamente
    return feedback_service.create(db, feedback, current_user)
```

---

### 5. Schema Validation (Pydantic)
**Patrón**: Validación automática con type hints
```python
from pydantic import BaseModel, validator, EmailStr

class UserCreate(BaseModel):
    email: EmailStr  # Validación automática de email
    username: str
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "strongpass123"
            }
        }
```

---

### 6. Factory Pattern (ML Model Loading)
**Patrón**: Creación de objetos complejos
```python
class ModelFactory:
    _instance = None
    
    @classmethod
    def get_model(cls):
        if cls._instance is None:
            cls._instance = ResNet50(weights='imagenet')
            print("Model loaded into memory")
        return cls._instance

# Uso: singleton pattern para evitar múltiples cargas
model = ModelFactory.get_model()
```

---

## Deployment y Containerización

### Docker Multi-Stage Builds

**API Dockerfile** (ejemplo):
```dockerfile
# Stage 1: Base
FROM python:3.8.13 AS base
WORKDIR /src
COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Testing
FROM base AS test
COPY ./ /src/
RUN ["python", "-m", "pytest", "-v", "tests"]

# Stage 3: Production Build
FROM base AS build
COPY ./ /src/
ENV PYTHONPATH=/src
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:5000", "main:app"]
```

**Ventajas Multi-Stage**:
- Imagen final más pequeña (no incluye testing deps)
- Tests ejecutados durante build
- Capas cacheadas para builds rápidos

---

### Docker Compose Orchestration

**Servicios Definidos**:
```yaml
version: "3.2"
services:
  # Database
  db:
    image: postgres:13-alpine
    environment:
      POSTGRES_DB: sp3
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    networks:
      - shared_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:6.2.6
    networks:
      - shared_network

  # API
  api:
    build:
      context: ./api
      target: build
    depends_on:
      - redis
      - model
      - db
    ports:
      - "8000:5000"
    volumes:
      - ./uploads:/src/uploads
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      DATABASE_HOST: db
      SECRET_KEY: ${SECRET_KEY}
    networks:
      - shared_network

  # ML Service (Scalable)
  model:
    build:
      context: ./model
    depends_on:
      - redis
    volumes:
      - ./uploads:/src/uploads
    networks:
      - shared_network
    # No container_name para permitir scaling

  # UI
  ui:
    build:
      context: ./ui
      target: build
    depends_on:
      - api
    ports:
      - "9090:9090"
    environment:
      - API_HOST=api
      - API_PORT=5000
    networks:
      - shared_network

networks:
  shared_network:
    external: true

volumes:
  postgres_data:
```

**Comandos de Deployment**:
```bash
# 1. Crear red externa
docker network create shared_network

# 2. Build y start servicios
docker-compose up -d

# 3. Poblar base de datos
docker exec ml_api python populate_db.py

# 4. Escalar ML service
docker-compose up -d --scale model=3

# 5. Ver logs
docker-compose logs -f model

# 6. Restart servicio específico
docker-compose restart api

# 7. Stop y cleanup
docker-compose down -v
```

---

### Volúmenes y Persistencia

**Volúmenes Definidos**:
1. **postgres_data**: Persistencia de base de datos
   - Tipo: Named volume
   - Ubicación: `/var/lib/postgresql/data`
   - Sobrevive a `docker-compose down`

2. **uploads**: Shared filesystem para imágenes
   - Tipo: Bind mount
   - Host: `./uploads`
   - Containers: `/src/uploads`
   - Shared entre: API, ML Service

**Estrategia de Backups**:
```bash
# Backup PostgreSQL
docker exec postgres_db pg_dump -U postgres sp3 > backup.sql

# Restore
docker exec -i postgres_db psql -U postgres sp3 < backup.sql

# Backup uploads
tar -czf uploads_backup.tar.gz uploads/
```

---

## Escalabilidad y Performance

### Escalabilidad Horizontal

**ML Service Scaling**:
```bash
# Escalar a N workers
docker-compose up -d --scale model=N

# Cada worker:
# - Memoria: ~500MB (modelo + overhead)
# - CPU: 1 core recomendado
# - Throughput: ~5-10 predictions/second
```

**Cálculo de Capacidad**:
```
Usuarios concurrentes = 100
Predictions/user/min = 2
Total predictions/min = 200

Con 1 worker (10 pred/sec = 600 pred/min):
  Capacidad = 600 pred/min
  Overhead = 30%
  Real capacity = 420 pred/min ✓ (suficiente)

Con carga pico 500 pred/min:
  Workers necesarios = 500 / 420 ≈ 2 workers
```

---

### Performance Optimization

**1. Database Indexing**:
```sql
-- Índices creados
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_created_at ON feedback(created_at DESC);
```

**2. Redis TTL para Results**:
```python
# Resultados expiran en 5 minutos
redis.set(f'result:{job_id}', result, ex=300)
```

**3. Connection Pooling**:
```python
# SQLAlchemy pool
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

**4. Gunicorn Workers**:
```bash
# 4 workers para API
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

**5. Image Preprocessing Caching**:
```python
# Cache preprocessing en Redis (opcional)
preprocessed_key = f'preprocessed:{hash}'
if redis.exists(preprocessed_key):
    img_array = pickle.loads(redis.get(preprocessed_key))
else:
    img_array = preprocess_image(image_path)
    redis.set(preprocessed_key, pickle.dumps(img_array), ex=3600)
```

---

### Monitoring y Observability

**Métricas Clave**:
```python
# API metrics (Prometheus-style)
- http_requests_total{endpoint="/predict", status="200"}
- http_request_duration_seconds{endpoint="/predict"}
- redis_queue_length
- ml_prediction_duration_seconds
- database_query_duration_seconds

# System metrics
- container_memory_usage_bytes
- container_cpu_usage_percent
- redis_connected_clients
- postgres_active_connections
```

**Health Checks**:
```python
# API Health Endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": check_db_connection(),
        "redis": check_redis_connection(),
        "ml_workers": get_worker_count()
    }
```

---

## Testing Strategy

### Test Pyramid

```
        /\
       /E2E\        ← Integration Tests (2 tests)
      /------\
     /  API   \     ← API Tests (9 tests)
    /----------\
   /   Unit     \   ← Unit Tests (6 tests)
  /--------------\
```

**1. Unit Tests** (Fast, Isolated):
- `test_utils.py`: File validation, hashing
- `test_model.py`: Model inference
- Individual functions

**2. API Tests** (Medium Speed):
- `test_router_user.py`: User CRUD
- `test_router_model.py`: Prediction endpoint
- `test_router_feedback.py`: Feedback CRUD

**3. Integration Tests** (Slow, E2E):
- `test_integration.py`: Full flow con servicios reales
- Login → Predict → Feedback

**4. Stress Tests** (Performance):
- Locust: 10-100 usuarios concurrentes
- Medición de throughput, latency, error rate

---

### Stress Testing con Locust

**Configuración**:
```python
class APIUser(HttpUser):
    wait_time = between(1, 5)  # Random wait 1-5s
    
    def on_start(self):
        # Login once per user
        self.token = login("admin@example.com", "admin")
    
    @task(3)  # 75% del tráfico
    def predict_image(self):
        with open("dog.jpeg", "rb") as f:
            files = {"file": ("dog.jpeg", f, "image/jpeg")}
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.post("/model/predict", 
                           headers=headers, 
                           files=files)
    
    @task(1)  # 25% del tráfico
    def view_docs(self):
        self.client.get("/docs")
```

**Ejecución**:
```bash
# Headless mode (CI/CD)
locust -f locustfile.py \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html report.html

# Web UI mode (desarrollo)
locust -f locustfile.py --host=http://localhost:8000
# Abrir http://localhost:8089
```

**Resultados Ejemplo**:
```
Escenario: 10 usuarios, 30 segundos

Con 1 worker ML:
- Requests: 91
- RPS: 3.17
- Avg latency: 128ms
- 95th percentile: 280ms
- Failures: 0%

Con 3 workers ML:
- Requests: 94
- RPS: 3.22 (+1.6%)
- Avg latency: 127ms
- 95th percentile: 230ms (-17.9%)
- Failures: 0%
```

---

## Security Considerations

### 1. Authentication & Authorization
- **JWT tokens**: HS256 signing
- **Password hashing**: bcrypt with salt
- **Token expiration**: Configurable (default 30min)
- **Protected endpoints**: Bearer token required

### 2. Input Validation
```python
# File upload validation
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_image(file):
    # Check extension
    if not allowed_file(file.filename):
        raise HTTPException(400, "File type is not supported.")
    
    # Check size
    file.file.seek(0, 2)
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    file.file.seek(0)
```

### 3. SQL Injection Prevention
- **SQLAlchemy ORM**: Parameterized queries automáticas
- **No raw SQL**: Excepto migrations controladas

### 4. Environment Variables
```bash
# Secrets en .env (never committed)
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=secure-password
```

### 5. CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9090"],  # UI origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Conclusiones y Mejoras Futuras

### Sistema Actual
✅ Arquitectura de microservicios desacoplada  
✅ Procesamiento ML asíncrono y escalable  
✅ Autenticación JWT robusta  
✅ Tests completos (unit, integration, stress)  
✅ Containerización completa  
✅ Documentación exhaustiva  

### Posibles Mejoras

**1. Caching de Predicciones**:
```python
# Cache predicciones por hash de imagen
prediction_cache = redis.get(f'pred:{image_hash}')
if prediction_cache:
    return json.loads(prediction_cache)
```

**2. Kubernetes Deployment**:
- Helm charts para deployment
- Horizontal Pod Autoscaler para ML workers
- Persistent Volume Claims para PostgreSQL

**3. Observability**:
- Prometheus + Grafana para métricas
- ELK stack para logs centralizados
- Distributed tracing con Jaeger

**4. CI/CD Pipeline**:
```yaml
# .github/workflows/deploy.yml
- Build & test Docker images
- Push to registry
- Deploy to staging
- Run E2E tests
- Deploy to production
```

**5. Model Versioning**:
- Soporte para múltiples versiones de modelo
- A/B testing de modelos
- Model registry (MLflow)

**6. Advanced ML Features**:
- Custom fine-tuning del modelo
- Feedback loop para retraining
- Confidence threshold tuning
- Multi-model ensemble

**7. Security Enhancements**:
- OAuth2 con refresh tokens
- Rate limiting por usuario
- File virus scanning
- HTTPS/TLS termination

**8. Database Optimization**:
- Read replicas para queries
- Connection pooling con PgBouncer
- Partitioning de tabla feedback por fecha

---

## Referencias y Recursos

### Documentación Oficial
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
- [TensorFlow/Keras](https://www.tensorflow.org/api_docs)
- [Redis](https://redis.io/documentation)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Docker Compose](https://docs.docker.com/compose/)

### Modelos y Datasets
- [ResNet50 Paper](https://arxiv.org/abs/1512.03385)
- [ImageNet Dataset](https://www.image-net.org/)
- [Keras Applications](https://keras.io/api/applications/)

### Mejores Prácticas
- [12-Factor App](https://12factor.net/)
- [Microservices Patterns](https://microservices.io/patterns/index.html)
- [REST API Design](https://restfulapi.net/)

---

**Autor**: Sistema ML Image Classifier  
**Fecha**: Diciembre 2025  
**Versión**: 1.0.0  
**Repositorio**: https://github.com/ingenieroiansuarez/ml-image-classifier
