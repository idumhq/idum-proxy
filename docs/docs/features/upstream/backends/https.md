# HTTPS

### Connection pooling

For each endpoint, a connection pooling is created with a session.
The session is reused by others requests, depending the TTL of the connection (keep-alive). 
If the TTL is expired, a new session is created with a TTL of 0.
