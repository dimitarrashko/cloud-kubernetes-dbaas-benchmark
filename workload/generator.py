import argparse
import asyncio
import csv
import math
import os
import statistics
import time
from datetime import datetime, timezone

import aiohttp


async def send_request(session, url):
    start = time.perf_counter()

    try:
        async with session.get(url) as response:
            if response.status != 200:
                text = await response.text()
                print(f"HTTP {response.status}: {text[:200]}")


            await response.read()

            latency = time.perf_counter() - start

            return {
                "success": response.status == 200,
                "latency": latency,
            }

    except Exception as e:
        print(f"Request failed: {type(e).__name__}: {e}")

        return {
            "success": False,
            "latency": time.perf_counter() - start,
    }


async def run_test(url, rps, duration, provider, mode, output):
    total_requests = rps * duration

    timeout = aiohttp.ClientTimeout(total=120)

    # 0 means aiohttp doesn't impose its normal small connection limit.
    connector = aiohttp.TCPConnector(limit=0)

    tasks = []

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:

        loop = asyncio.get_running_loop()

        test_start = loop.time()

        for i in range(total_requests):
            target_time = test_start + (i / rps)

            wait = target_time - loop.time()

            if wait > 0:
                await asyncio.sleep(wait)

            tasks.append(
                asyncio.create_task(
                    send_request(session, url)
                )
            )

        results = await asyncio.gather(*tasks)

        test_end = loop.time()

    successful_latencies = [
        result["latency"]
        for result in results
        if result["success"]
    ]

    successful = len(successful_latencies)
    failed = total_requests - successful

    wall_time = test_end - test_start

    if successful_latencies:
        average_latency = statistics.mean(successful_latencies)

        ordered = sorted(successful_latencies)

        p95_index = max(
            0,
            math.ceil(0.95 * len(ordered)) - 1
        )

        p95_latency = ordered[p95_index]

    else:
        average_latency = 0
        p95_latency = 0

    throughput = (
        successful / wall_time
        if wall_time > 0
        else 0
    )

    success_rate = (
        successful / total_requests * 100
        if total_requests > 0
        else 0
    )

    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "mode": mode,
        "target_rps": rps,
        "duration_s": duration,
        "total_requests": total_requests,
        "successful": successful,
        "failed": failed,
        "success_rate_percent": success_rate,
        "avg_latency_s": average_latency,
        "p95_latency_s": p95_latency,
        "wall_time_s": wall_time,
        "throughput_rps": throughput,
    }

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    exists = os.path.exists(output)

    with open(output, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=row.keys()
        )

        if not exists:
            writer.writeheader()

        writer.writerow(row)

    print()
    print("=" * 45)
    print(f"Provider:          {provider}")
    print(f"Mode:              {mode}")
    print(f"Target RPS:        {rps}")
    print(f"Duration:          {duration}s")
    print(f"Total requests:    {total_requests}")
    print(f"Successful:        {successful}")
    print(f"Failed:            {failed}")
    print(f"Success rate:      {success_rate:.2f}%")
    print(f"Average latency:   {average_latency:.3f}s")
    print(f"P95 latency:       {p95_latency:.3f}s")
    print(f"Throughput:        {throughput:.2f} req/s")
    print("=" * 45)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--url", required=True)
    parser.add_argument("--rps", type=int, required=True)
    parser.add_argument("--duration", type=int, default=30)

    parser.add_argument(
        "--provider",
        choices=["local", "aws", "azure"],
        required=True,
    )

    parser.add_argument("--mode", required=True)

    parser.add_argument(
        "--output",
        default="results/results.csv",
    )

    args = parser.parse_args()

    asyncio.run(
        run_test(
            args.url,
            args.rps,
            args.duration,
            args.provider,
            args.mode,
            args.output,
        )
    )


if __name__ == "__main__":
    main()
