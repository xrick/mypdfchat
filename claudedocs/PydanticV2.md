# Pydantic V2 Data Models in DocAI

**Document Version**: 1.0
**Date**: 2025-10-30
**Pydantic Version**: V2 (2.x)
**FastAPI Integration**: Native Support

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Why Pydantic V2?](#why-pydantic-v2)
3. [Model Definition Patterns](#model-definition-patterns)
4. [DocAI's Current Models](#docais-current-models)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)
8. [Migration Guide](#migration-guide)

---

## Introduction

### What is Pydantic?

Pydantic is a **data validation and settings management** library for Python, using Python type annotations. It's the standard for FastAPI applications.

### Key Features

- ✅ **Runtime type validation**: Automatic data validation using type hints
- ✅ **Serialization/Deserialization**: JSON ↔ Python object conversion
- ✅ **OpenAPI generation**: Automatic API documentation
- ✅ **IDE support**: Full type checking and autocompletion
- ✅ **Performance**: Rust-based core in V2 (10-50x faster than V1)

---

## Why Pydantic V2?

### Decorator vs Class-Based Models

**You asked about decorator-based models**. Here's the comparison:

#### ❌ Python @dataclass (NOT used in DocAI)

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
```

**Limitations**:
- ❌ No runtime validation
- ❌ No automatic JSON serialization
- ❌ No FastAPI OpenAPI integration
- ❌ Manual validation required

#### ✅ Pydantic BaseModel (Used in DocAI)

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
```

**Advantages**:
- ✅ Automatic runtime validation
- ✅ Built-in JSON serialization
- ✅ FastAPI automatic OpenAPI docs
- ✅ Type-safe with IDE support

### Why No Decorators?

**Pydantic V2 philosophy**: Inheritance over decoration

```python
# ✅ Pydantic V2 Standard (Class Inheritance)
class Model(BaseModel):
    field: str

# ❌ Not Pydantic style (Decorator approach)
@pydantic_model  # ← This doesn't exist in Pydantic V2
class Model:
    field: str
```

**Exception**: Validators use decorators

```python
class Model(BaseModel):
    email: str

    @field_validator('email')  # ← Decorator for validation logic
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

---

## Model Definition Patterns

### Basic Model

```python
from pydantic import BaseModel

class User(BaseModel):
    """Basic user model"""
    id: int
    name: str
    email: str
    is_active: bool = True  # Default value
```

**Usage**:
```python
# Create instance
user = User(id=1, name="Alice", email="alice@example.com")

# Access fields
print(user.name)  # "Alice"

# JSON serialization
print(user.model_dump_json())  # '{"id":1,"name":"Alice",...}'

# Validation (automatic)
try:
    User(id="invalid", name="Bob", email="bob@example.com")
except ValidationError as e:
    print(e)  # Validation error: id must be int
```

### Model with Field Validation

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    """User with field constraints"""
    id: int = Field(..., gt=0, description="User ID")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(..., ge=0, le=150)
```

**Field Parameters**:
- `...` = Required field (no default)
- `gt`, `ge`, `lt`, `le` = Greater than, greater/equal, less than, less/equal
- `min_length`, `max_length` = String/list length constraints
- `pattern` = Regex validation
- `description` = OpenAPI documentation

### Model with Custom Validators

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    username: str
    password: str

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Username must be alphanumeric"""
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()  # Normalize to lowercase

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Password must be strong"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        return v
```

### Model with Config

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    """User with configuration"""
    model_config = ConfigDict(
        str_strip_whitespace=True,      # Auto-strip strings
        validate_assignment=True,        # Validate on attribute assignment
        arbitrary_types_allowed=False,   # Only allow known types
        frozen=False                     # Allow mutation (default)
    )

    name: str
    email: str
```

### Model with Example Schema

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    """User with OpenAPI example"""
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Full name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Alice Smith"
            }
        }
    )
```

---

## DocAI's Current Models

### Overview

DocAI defines **10 core models** in [app/models/schemas.py](../app/models/schemas.py):

```
app/models/
└── schemas.py
    ├── UploadResponse          (File upload)
    ├── ChatRequest             (Chat input)
    ├── ChatResponse            (Chat output)
    ├── MessageSchema           (Single message)
    ├── SessionResponse         (Session history)
    ├── SessionListResponse     (Session list)
    ├── ExportFormat            (Enum)
    ├── ExportRequest           (Export config)
    ├── QueryExpansion          (Query enhancement)
    ├── ErrorResponse           (Error handling)
    └── HealthCheckResponse     (System health)
```

### Example 1: UploadResponse

**File**: [app/models/schemas.py:17-36](../app/models/schemas.py#L17-L36)

```python
class UploadResponse(BaseModel):
    """Response model for file upload"""
    file_id: str = Field(..., description="Unique identifier for uploaded file")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    chunk_count: int = Field(..., description="Number of text chunks generated")
    embedding_status: str = Field(..., description="Status: 'pending', 'completed', 'failed'")
    message: str = Field(default="File uploaded and indexed successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123def456",
                "filename": "document.pdf",
                "file_size": 1024000,
                "chunk_count": 150,
                "embedding_status": "completed",
                "message": "File uploaded and indexed successfully"
            }
        }
```

**Usage in Endpoint**:
```python
from fastapi import APIRouter
from app.models.schemas import UploadResponse

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile):
    # Process file...
    return UploadResponse(
        file_id="file_123",
        filename=file.filename,
        file_size=len(content),
        chunk_count=50,
        embedding_status="completed"
    )
```

### Example 2: ChatRequest with Validation

**File**: [app/models/schemas.py:43-90](../app/models/schemas.py#L43-L90)

```python
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to search")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages"
    )
    enable_query_enhancement: Optional[bool] = Field(
        default=True,
        description="Enable Strategy 2 Query Expansion"
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve"
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, v):
        """Ensure at least one file_id is provided"""
        if not v or len(v) == 0:
            raise ValueError("At least one file_id is required")
        return v
```

**Key Features**:
- ✅ String length validation: `min_length=1, max_length=2000`
- ✅ List constraints: `min_items=1`
- ✅ Numeric ranges: `ge=1, le=20` (greater/equal, less/equal)
- ✅ Custom validator: `@field_validator` for business logic
- ✅ Optional fields: `Optional[...]` with defaults

### Example 3: Enum Model

**File**: [app/models/schemas.py:236-240](../app/models/schemas.py#L236-L240)

```python
from enum import Enum

class ExportFormat(str, Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
```

**Usage**:
```python
class ExportRequest(BaseModel):
    format: ExportFormat = Field(default=ExportFormat.JSON)

# Usage
request = ExportRequest(format="json")  # Auto-validates
print(request.format)  # ExportFormat.JSON

# Invalid value
try:
    ExportRequest(format="xml")  # ❌ Raises ValidationError
except ValidationError:
    print("Invalid format!")
```

### Example 4: Nested Models

```python
class Address(BaseModel):
    """Address sub-model"""
    street: str
    city: str
    country: str
    zip_code: str = Field(..., pattern=r'^\d{5}$')

class User(BaseModel):
    """User with nested address"""
    name: str
    email: str
    address: Address  # Nested model

# Usage
user = User(
    name="Alice",
    email="alice@example.com",
    address={
        "street": "123 Main St",
        "city": "San Francisco",
        "country": "USA",
        "zip_code": "94102"
    }
)

print(user.address.city)  # "San Francisco"
```

---

## Advanced Features

### 1. Model Composition (Inheritance)

```python
class BaseUser(BaseModel):
    """Base user fields"""
    id: int
    name: str
    email: str

class AdminUser(BaseUser):
    """Admin extends base user"""
    permissions: List[str]
    is_superuser: bool = False

class GuestUser(BaseUser):
    """Guest extends base user"""
    session_expires: datetime
```

### 2. Generic Models

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

DataT = TypeVar('DataT')

class Response(BaseModel, Generic[DataT]):
    """Generic API response"""
    success: bool
    data: DataT
    message: str

# Usage
class UserData(BaseModel):
    id: int
    name: str

user_response = Response[UserData](
    success=True,
    data=UserData(id=1, name="Alice"),
    message="User retrieved successfully"
)
```

### 3. Computed Fields

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        """Computed area property"""
        return self.width * self.height

# Usage
rect = Rectangle(width=10, height=5)
print(rect.area)  # 50.0 (automatically computed)
```

### 4. Model Validators (Root)

```python
from pydantic import BaseModel, model_validator

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode='after')
    def validate_date_range(self) -> 'DateRange':
        """Ensure end_date is after start_date"""
        if self.end_date <= self.start_date:
            raise ValueError('end_date must be after start_date')
        return self
```

### 5. Serialization Customization

```python
from pydantic import BaseModel, field_serializer

class User(BaseModel):
    name: str
    password: str

    @field_serializer('password')
    def hide_password(self, value: str) -> str:
        """Hide password in serialization"""
        return "***HIDDEN***"

# Usage
user = User(name="Alice", password="secret123")
print(user.model_dump())
# {'name': 'Alice', 'password': '***HIDDEN***'}
```

---

## Best Practices

### 1. Use Type Hints Everywhere

```python
# ✅ GOOD: Explicit types
class User(BaseModel):
    name: str
    age: int
    tags: List[str]
    metadata: Dict[str, Any]

# ❌ BAD: No type hints
class User(BaseModel):
    name = "Alice"
    age = 30
```

### 2. Provide Descriptions

```python
# ✅ GOOD: Documented fields
class User(BaseModel):
    id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., description="Full name of user")

# ❌ BAD: No documentation
class User(BaseModel):
    id: int
    name: str
```

### 3. Add Examples for OpenAPI

```python
# ✅ GOOD: Includes example
class User(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": 1, "name": "Alice Smith"}
        }
    )

# ❌ BAD: No example
class User(BaseModel):
    id: int
    name: str
```

### 4. Use Validators for Business Logic

```python
# ✅ GOOD: Validation in model
class Order(BaseModel):
    quantity: int
    price: float

    @field_validator('quantity')
    @classmethod
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

# ❌ BAD: Validation in endpoint
@app.post("/order")
def create_order(order: Order):
    if order.quantity <= 0:  # Should be in model!
        raise HTTPException(400, "Invalid quantity")
```

### 5. Separate Request/Response Models

```python
# ✅ GOOD: Separate models
class UserCreate(BaseModel):
    """Request model (no id)"""
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    """Response model (with id, no password)"""
    id: int
    name: str
    email: str

# ❌ BAD: Single model for both
class User(BaseModel):
    id: Optional[int] = None  # Confusing!
    name: str
    email: str
    password: Optional[str] = None  # Security issue!
```

---

## Common Patterns

### Pattern 1: Pagination Response

```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

# Usage
class User(BaseModel):
    id: int
    name: str

users_page = PaginatedResponse[User](
    items=[User(id=1, name="Alice"), User(id=2, name="Bob")],
    total=100,
    page=1,
    page_size=10,
    has_next=True,
    has_prev=False
)
```

### Pattern 2: API Wrapper

```python
class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Usage
@app.get("/user/{id}", response_model=APIResponse[User])
async def get_user(id: int):
    user = await db.get_user(id)
    return APIResponse(success=True, data=user)
```

### Pattern 3: Multi-Step Validation

```python
class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    password_confirm: str

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username too short')
        return v.lower()

    @field_validator('email')
    @classmethod
    def email_valid(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
```

---

## Migration Guide

### From Python dataclass to Pydantic

**Before (dataclass)**:
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
```

**After (Pydantic)**:
```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0)
```

### From Dict-Based to Pydantic

**Before (dict)**:
```python
def create_user(data: dict) -> dict:
    # Manual validation
    if 'name' not in data:
        raise ValueError("Name required")
    if not isinstance(data['age'], int):
        raise ValueError("Age must be int")
    return {"id": 1, "name": data['name'], "age": data['age']}
```

**After (Pydantic)**:
```python
class UserCreate(BaseModel):
    name: str
    age: int

class UserResponse(BaseModel):
    id: int
    name: str
    age: int

def create_user(data: UserCreate) -> UserResponse:
    # Automatic validation!
    return UserResponse(id=1, name=data.name, age=data.age)
```

---

## Summary

### Why Pydantic V2 in DocAI?

1. **Type Safety**: Full IDE support and type checking
2. **Validation**: Automatic runtime validation
3. **FastAPI Integration**: Native OpenAPI documentation
4. **Performance**: Rust-based core (V2)
5. **Maintainability**: Clear, explicit data contracts

### Key Takeaways

- ✅ **Use BaseModel inheritance**, not decorators
- ✅ **Add Field() with constraints** for validation
- ✅ **Use @field_validator** for custom logic
- ✅ **Provide examples** for OpenAPI docs
- ✅ **Separate request/response models** for clarity

### DocAI Model Architecture

```
API Request → Pydantic Validation → Business Logic → Pydantic Response
     ↓              ↓                      ↓                ↓
  ChatRequest   Type Check          Process Query     ChatResponse
                Field Rules         LLM Call          JSON Output
                Custom Validators   RAG Pipeline      OpenAPI Docs
```

---

## Additional Resources

### Official Documentation
- [Pydantic V2 Docs](https://docs.pydantic.dev/latest/)
- [FastAPI Pydantic Models](https://fastapi.tiangolo.com/tutorial/body/)

### DocAI Implementation
- [app/models/schemas.py](../app/models/schemas.py) - All current models
- [app/api/v1/endpoints/chat.py](../app/api/v1/endpoints/chat.py) - Usage examples
- [app/api/v1/endpoints/upload.py](../app/api/v1/endpoints/upload.py) - Upload models

---

*Document created: 2025-10-30 | DocAI Project | Pydantic V2 Guide*
