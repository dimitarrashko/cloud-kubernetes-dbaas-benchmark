# Performance Evaluation of Managed Kubernetes and Database-as-a-Service on AWS and Microsoft Azure

A comparative performance and scalability study of managed Kubernetes and database services on **Amazon Web Services (AWS)** and **Microsoft Azure**.

## Overview

This project evaluates the performance of containerized workloads deployed on managed Kubernetes clusters connected to managed PostgreSQL databases.

A FastAPI application performs CPU-intensive hashing, enforces a minimum processing duration of five seconds, and stores the result of each successful request in PostgreSQL.

An asynchronous Python workload generator simulates different traffic levels to evaluate application performance, Kubernetes autoscaling behavior, and system elasticity.

## Architecture

Both cloud environments use the same application and workload generator.

**AWS**
- Amazon Elastic Kubernetes Service (EKS)
- Amazon Elastic Container Registry (ECR)
- Amazon RDS for PostgreSQL
- Kubernetes LoadBalancer Service

**Microsoft Azure**
- Azure Kubernetes Service (AKS)
- Azure Container Registry (ACR)
- Azure Database for PostgreSQL Flexible Server
- Azure LoadBalancer Service

Each deployment uses two worker nodes. PostgreSQL is accessed through private cloud networking.

## Application

The FastAPI application exposes two endpoints:

- `/health` – checks application availability.
- `/work` – performs CPU-intensive SHA-256 hashing, maintains a minimum five-second processing duration, and inserts a result into PostgreSQL.

## Workload Generator

The workload generator is implemented in Python using `asyncio` and `aiohttp`.

It generates concurrent HTTP requests at configurable target rates and records:
- Total, successful and failed requests
- Success rate
- Average response latency
- 95th percentile latency
- Achieved throughput
- Total execution time

The benchmark evaluates target loads ranging from 1 to 1,000 requests per second, using 60-second test durations.

## Kubernetes Autoscaling

Horizontal Pod Autoscaling (HPA) is configured with:

| Parameter | Configuration |
|---|---|
| Minimum replicas | 1 |
| Maximum replicas | 10 |
| CPU utilization target | 60% |
| Scale-down stabilization | 120 seconds |

The configuration is used to evaluate how each platform responds to increasing and decreasing workloads.

## Benchmark Methodology

Three aspects of performance are evaluated:

1. **Execution performance:** Single-pod and HPA-enabled execution time, latency and throughput.
2. **Scalability:** Changes in performance as the target request rate increases.
3. **Elasticity:** A low–high–low workload sequence (10 → 100 → 10 RPS) to observe scaling and recovery behavior.

Speedup is calculated by comparing single-pod execution time against HPA-enabled execution time at the same target load.

## Results

The repository includes the raw benchmark CSV files, generated plots and the final technical report.

The evaluated metrics include execution time, throughput, speedup, and elasticity.

The report discusses performance differences, saturation behavior, autoscaling response and resource utilization across both cloud providers.

## Repository Structure

- `app.py` – FastAPI workload application
- `Dockerfile` – application container definition
- `workload/` – asynchronous load generator
- `kubernetes/` – deployment, service and HPA manifests
- `scripts/` – benchmark plotting scripts
- `results/` – raw measurements and plots
- `report/` – LaTeX documentation and compiled report


## Deployment Status

The AWS and Azure environments were deployed and benchmarked as part of the project. Cloud resources were intentionally decommissioned after data collection to avoid ongoing infrastructure costs.

The source code, Kubernetes configurations, benchmark results and technical report are retained in this repository. Recreating the cloud deployments requires an appropriately configured AWS or Azure account and the necessary permissions.

## Technologies

Python, FastAPI, asyncio, aiohttp, PostgreSQL, Docker, Kubernetes, Horizontal Pod Autoscaling, AWS EKS, AWS ECR, Amazon RDS, Azure AKS, Azure Container Registry, Azure Database for PostgreSQL, Bash and LaTeX.
