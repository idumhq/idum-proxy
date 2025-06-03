"""
# Demonstration
import asyncio
import logging
import threading
import time

import pytest

from idum_proxy.networking.connection_pooling.http_client import HTTPClient, event_loop_manager, safe_singleton
from idum_proxy.networking.connection_pooling.tracing.default_trace_handler import TraceHandlers
import aiohttp

# Demonstration
async def demonstrate_safe_patterns():
    Show all safe patterns working

    print("✅ Safe patterns demonstration:")

    strategies = ["dedicated", "thread_local", "context_var", "event_loop", "singleton"]

    async def test_strategy(strategy: str):
        async with HTTPClient(connector_strategy=strategy) as client:
            async with client.session.get('https://httpbin.org/get') as resp:
                print(f"  {strategy}: {resp.status}")

    # All these run safely in the same event loop
    await asyncio.gather(*[test_strategy(s) for s in strategies])


async def demonstrate_tracing():
    Show tracing capabilities

    print("\n🔍 Tracing demonstration:")

    # Basic tracing
    trace_config = TraceHandlers(
        enable_logging=True,
        log_level=logging.INFO,
        logger_name="demo.http"
    )

    async with HTTPClient(
            connector_strategy="dedicated",
            trace_handlers=trace_config
    ) as client:
        async with client.session.get('https://httpbin.org/get') as resp:
            print(f"  Basic tracing: {resp.status}")


async def demonstrate_dns_tracing():
    Show DNS resolution tracing

    print("\n🌐 DNS resolution tracing:")

    dns_lookups = []

    async def track_dns_start(session, trace_config_ctx, params):
        print(f"  🔍 DNS lookup starting for {params.host}")
        trace_config_ctx.dns_start = time.perf_counter()

    async def track_dns_end(session, trace_config_ctx, params):
        duration = time.perf_counter() - getattr(trace_config_ctx, 'dns_start', time.perf_counter())
        dns_lookups.append((params.host, duration))
        print(f"  ✅ DNS resolved for {params.host} in {duration:.3f}s")

    # Setup DNS tracing
    trace_config = TraceHandlers(
        enable_logging=False,  # Use custom handlers only
        on_dns_resolvehost_start=track_dns_start,
        on_dns_resolvehost_end=track_dns_end,
    )

    async with HTTPClient(
            connector_strategy="dedicated",  # Use dedicated to force new connections
            trace_handlers=trace_config
    ) as client:
        # Hit different hosts to trigger DNS lookups
        hosts = [
            'https://httpbin.org/get',
            'https://google.com',
            'https://github.com',
        ]

        for url in hosts:
            try:
                async with client.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    print(f"    Response from {resp.url.host}: {resp.status}")
            except Exception as e:
                print(f"    Error accessing {url}: {e}")

    print(f"  📊 DNS lookups performed: {len(dns_lookups)}")
    for host, duration in dns_lookups:
        print(f"    {host}: {duration:.3f}s")


async def demonstrate_custom_trace_handlers():
    Show custom trace handlers for metrics

    print("\n📊 Custom trace handlers:")

    # Custom metrics collector
    request_count = 0
    total_time = 0.0

    async def custom_request_start(session, trace_config_ctx, params):
        nonlocal request_count
        request_count += 1
        # Store start time directly on the context object
        trace_config_ctx.start_time = time.perf_counter()
        print(f"  🚀 Request #{request_count}: {params.method} {params.url}")

    async def custom_request_end(session, trace_config_ctx, params):
        nonlocal total_time
        # Get start time from the context object
        duration = time.perf_counter() - getattr(trace_config_ctx, 'start_time', time.perf_counter())
        total_time += duration
        print(f"  ✅ Completed in {duration:.3f}s (avg: {total_time / request_count:.3f}s)")

    async def custom_connection_reuse(session, trace_config_ctx, params):
        print("  🔄 Reusing connection")

    # Setup custom handlers
    trace_config = TraceHandlers(
        enable_logging=False,  # Disable default logging
        on_request_start=custom_request_start,
        on_request_end=custom_request_end,
        on_connection_reuseconn=custom_connection_reuse,
    )

    async with HTTPClient(
            connector_strategy="dedicated",
            trace_handlers=trace_config
    ) as client:
        # Make multiple requests to see connection reuse
        urls = [
            'https://httpbin.org/get',
            'https://httpbin.org/ip',
            'https://httpbin.org/uuid'
        ]

        for url in urls:
            async with client.session.get(url) as resp:
                pass  # Custom handlers will log everything

    print(f"  📈 Total requests: {request_count}, Total time: {total_time:.3f}s")


async def demonstrate_comprehensive_tracing():
    Show all trace events working together

    print("\n📋 Comprehensive tracing demonstration:")

    events = []

    async def log_event(event_type):
        Factory function to create event loggers

        async def handler(session, trace_config_ctx, params):
            timestamp = time.perf_counter()
            event_info = {
                'type': event_type,
                'time': timestamp,
                'params': params
            }
            events.append(event_info)

            if event_type == 'request_start':
                trace_config_ctx.request_start = timestamp
                print(f"  📤 {params.method} {params.url}")
            elif event_type == 'request_end':
                duration = timestamp - getattr(trace_config_ctx, 'request_start', timestamp)
                print(f"  📥 {params.response.status} ({duration:.3f}s)")
            elif event_type == 'dns_start':
                print(f"  🌐 DNS lookup: {params.host}")
            elif event_type == 'connection_create':
                print("  🔗 New connection ")
            elif event_type == 'connection_reuse':
                print("  🔄 Reuse connection ")

        return handler

    # Setup comprehensive tracing
    trace_config = TraceHandlers(
        enable_logging=False,  # Use custom handlers
        on_request_start=await log_event('request_start'),
        on_request_end=await log_event('request_end'),
        on_dns_resolvehost_start=await log_event('dns_start'),
        on_connection_create_start=await log_event('connection_create'),
        on_connection_reuseconn=await log_event('connection_reuse'),
    )

    async with HTTPClient(
            connector_strategy="dedicated",
            trace_handlers=trace_config
    ) as client:
        # Make requests to see all events
        async with client.session.get('https://httpbin.org/get') as resp:
            pass
        async with client.session.get('https://httpbin.org/ip') as resp:  # Should reuse connection
            pass

    print(f"  📊 Total trace events captured: {len(events)}")
    event_types = {}
    for event in events:
        event_types[event['type']] = event_types.get(event['type'], 0) + 1

    for event_type, count in event_types.items():
        print(f"    {event_type}: {count}")


def demonstrate_multi_thread_safety():
    Show thread safety

    print("\n✅ Multi-thread safety:")

    async def worker(worker_id: int, strategy: str):
        trace_config = TraceHandlers(
            enable_logging=True,
            logger_name=f"worker_{worker_id}"
        )

        async with HTTPClient(
                connector_strategy=strategy,
                trace_handlers=trace_config
        ) as client:
            async with client.session.get('https://httpbin.org/get') as resp:
                print(f"  Thread {worker_id} ({strategy}): {resp.status}")

    def run_worker(worker_id: int, strategy: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(worker(worker_id, strategy))
        finally:
            loop.close()

    # Test different strategies across threads
    strategies = ["thread_local", "event_loop", "singleton"]
    threads = []

    for i, strategy in enumerate(strategies):
        thread = threading.Thread(target=run_worker, args=(i, strategy))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


@pytest.mark.asyncio
async def test_http_client():
    # Setup logging to see trace output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await demonstrate_safe_patterns()
    await demonstrate_tracing()
    await demonstrate_dns_tracing()
    await demonstrate_custom_trace_handlers()
    await demonstrate_comprehensive_tracing()
    demonstrate_multi_thread_safety()

    # Cleanup (optional, but good practice)
    await event_loop_manager.cleanup_all()
    await safe_singleton.cleanup()

"""
