# Welcome to Idum-Proxy


With Idum-Proxy, you can proxify backends api for simple adding new features of backend api.


By example with the api of github, a new url `/proxy/github-api` is configured to call the api github and to save the result in a cache.
The next calls read the data in the cache and don't call the
```mermaid
graph LR
    Client[Client] -->|HTTPS<br/>/proxy/github-api| IdumProxy[idum-proxy] -->|HTTPS<br/>api.github.com| GitHubAPI[GitHub API]

    style Client fill:#f3e5f5,stroke:#4a148c
    style IdumProxy fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style GitHubAPI fill:#e8f5e8,stroke:#1b5e20
```
