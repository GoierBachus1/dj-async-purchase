# dj-async-purchase

Backend desarrollado con Django para simular un flujo de compras y procesamiento de pagos asíncronos.

El proyecto implementa productos, órdenes, reserva de inventario, pagos, máquinas de estados y procesamiento de tareas en segundo plano utilizando Celery y Redis.

## Características principales

- Gestión de productos e inventario.
- Creación de órdenes con múltiples productos.
- Reserva de stock mientras una orden está pendiente de pago.
- Procesamiento asíncrono de pagos con Celery y Redis.
- Máquinas de estados para órdenes y pagos.
- Reintentos de pago después de un intento fallido.
- Protección contra pagos activos duplicados.
- Idempotencia en el procesamiento de pagos.
- Cancelación de órdenes pendientes.
- Expiración automática de órdenes no pagadas.
- Liberación y confirmación automática del inventario.
- Validación de datos mediante Django REST Framework.

## Tecnologías

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- Celery
- Redis
- django-fsm
- Docker

## Arquitectura general

El flujo principal de una compra es:

```text
Cliente
   |
   v
Django REST API
   |
   +---- PostgreSQL
   |
   +---- Redis
           |
           v
         Celery
```

Django recibe y valida las solicitudes HTTP, mientras que PostgreSQL almacena productos, órdenes y pagos.

Las operaciones que deben ejecutarse de forma asíncrona son enviadas a Redis y procesadas por un worker de Celery.

## Flujo de compra

Al crear una orden:

```text
Producto
   |
   v
Crear orden
   |
   v
Validar stock
   |
   v
Reservar inventario
   |
   v
PENDING_PAYMENT
   |
   +-------------------+
   |                   |
   v                   v
Procesar pago       Expiración
   |                   |
   v                   v
Celery            Cancelar orden
   |
   +----------+
   |          |
   v          v
SUCCESS     FAILED
   |
   v
PAID
   |
   v
Confirmar stock
```

Cuando una orden es creada, el inventario se reserva pero todavía no se descuenta del stock físico.

Si el pago es exitoso, la reserva se confirma y el stock físico se reduce.

Si la orden es cancelada o expira, la reserva es liberada.

## Estados

### Order

Las órdenes utilizan una máquina de estados para controlar las transiciones permitidas.

```text
PENDING_PAYMENT
     |
     +----> PAID
     |
     +----> CANCELLED
```

Una orden pagada no puede cancelarse directamente.

### Payment

Los pagos manejan su propia máquina de estados:

```text
PENDING
   |
   v
PROCESSING
   |
   +----> SUCCEEDED
   |
   +----> FAILED
```

Un pago fallido permite realizar un nuevo intento mientras la orden continúe pendiente.

## Inventario

Cada producto mantiene:

- `stock`: inventario físico.
- `reserved_stock`: unidades reservadas por órdenes pendientes.
- `available_stock`: unidades disponibles para nuevas órdenes.

```text
available_stock = stock - reserved_stock
```

La reserva de inventario utiliza transacciones de base de datos y bloqueos para reducir problemas de concurrencia.

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd dj-async-purchase
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
```

En Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Variables de entorno

Crear un archivo `.env` basado en `.env.example`.

Ejemplo:

```env
SECRET_KEY=your-secret-key
DEBUG=True

DB_NAME=dj_async_purchase
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

> El archivo `.env` no debe almacenarse en el repositorio.

### 5. Ejecutar migraciones

```bash
python manage.py migrate
```

## Redis

El proyecto utiliza Redis como broker para Celery.

Puede ejecutarse mediante Docker:

```bash
docker run -d --name dj-async-redis -p 6379:6379 redis:7
```

Si el contenedor ya existe:

```bash
docker start dj-async-redis
```

Para verificar la conexión:

```bash
docker exec -it dj-async-redis redis-cli ping
```

Debe responder:

```text
PONG
```

## Ejecución

Para utilizar el proyecto se necesitan Django, Redis y un worker de Celery ejecutándose.

### Django

```bash
python manage.py runserver
```

### Celery

En Windows:

```bash
celery -A config worker -l info -P solo
```

La API estará disponible en:

```text
http://127.0.0.1:8000/
```

## API

### Products

```text
GET /api/products/
GET /api/products/{id}/
```

### Orders

```text
GET  /api/orders/
POST /api/orders/
GET  /api/orders/{id}/
POST /api/orders/{id}/cancel/
```

### Payments

```text
GET  /api/payments/
GET  /api/payments/{id}/
POST /api/payments/orders/{order_id}/
```

## Ejemplo de compra

### Consultar productos

```http
GET /api/products/
```

### Crear una orden

```http
POST /api/orders/
Content-Type: application/json
```

```json
{
    "items": [
        {
            "product_id": 1,
            "quantity": 2
        }
    ]
}
```

La orden será creada inicialmente con estado:

```text
pending_payment
```

y las unidades correspondientes quedarán reservadas.

### Procesar pago

```http
POST /api/payments/orders/{order_id}/
```

La API crea el pago y envía el procesamiento a Celery.

La respuesta utiliza `202 Accepted` porque el procesamiento continúa de manera asíncrona.

### Consultar pago

```http
GET /api/payments/{payment_id}/
```

Un pago procesado correctamente tendrá:

```json
{
    "status": "succeeded",
    "transaction_id": "TXN-1"
}
```

La orden asociada pasará a:

```text
paid
```

y el inventario reservado será confirmado.

## Expiración de órdenes

Cuando se crea una orden pendiente de pago se programa una tarea de Celery para verificarla posteriormente.

Si al ejecutarse la tarea la orden continúa en:

```text
pending_payment
```

la orden se cancela y el inventario reservado es liberado.

Actualmente el tiempo de expiración está configurado en **60 segundos para desarrollo y pruebas**.

Si la orden ya fue pagada cuando se ejecuta la tarea, la expiración es ignorada.

## Seguridad ante concurrencia

Las operaciones críticas utilizan:

```python
transaction.atomic()
```

y:

```python
select_for_update()
```

para proteger operaciones relacionadas con inventario y pagos concurrentes.

También se evita crear más de un pago activo (`pending` o `processing`) para la misma orden.

## Idempotencia

Las tareas de procesamiento de pagos verifican el estado actual antes de ejecutar nuevamente una operación.

Si Celery intenta procesar nuevamente un pago que ya está en estado `succeeded`, la tarea no vuelve a confirmar el pago ni a descontar inventario.

Ejemplo:

```json
{
    "payment_id": 10,
    "status": "already_succeeded"
}
```

## Validaciones

La API valida, entre otros casos:

- Órdenes sin productos.
- Cantidades menores a 1.
- Productos inexistentes o inactivos.
- Stock insuficiente.
- Cancelación de órdenes desde estados no permitidos.
- Pagos sobre órdenes que ya no están pendientes.
- Intentos de crear múltiples pagos activos para una misma orden.

## Estado actual

El proyecto cuenta actualmente con un flujo funcional de compra de principio a fin:

```text
Catálogo
   ↓
Creación de orden
   ↓
Reserva de stock
   ↓
Creación de pago
   ↓
Procesamiento asíncrono
   ↓
Confirmación de orden
   ↓
Actualización de inventario
```

El proyecto continúa en desarrollo. Entre los siguientes pasos se encuentran la incorporación de pruebas automatizadas, mejoras en el manejo de errores y configuración para distintos entornos.