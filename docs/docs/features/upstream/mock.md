# Mock

```json
{
  "upstream": {
    "mock": {
      "enabled": true,
      "path_templates": {
        "/users": {
          "status_code": 200,
          "content_type": "application/json",
          "body": {
            "users": [
              {
                "id": 1,
                "name": "John Doe"
              },
              {
                "id": 2,
                "name": "Jane Smith"
              }
            ]
          }
        },
        "/users/{id}": {
          "status_code": 200,
          "content_type": "application/json",
          "body": {
            "id": "${path.id}",
            "name": "User ${path.id}",
            "email": "user${path.id}@example.com"
          }
        }
      },
      "default_response": {
        "status_code": 404,
        "body": {
          "error": "Resource not found"
        }
      }
    }
  }
}
```