from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd



SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

RESULTS_DIR = PROJECT_ROOT / "results"

SINGLE_CSV = RESULTS_DIR / "aws_results.csv"
HPA_CSV = RESULTS_DIR / "aws_hpa_results.csv"
ELASTICITY_CSV = RESULTS_DIR / "aws_elasticity.csv"


OUTPUT_DIR = RESULTS_DIR / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_plot(filename: str) -> None:
    """Save every figure as both PNG and PDF."""
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{filename}.png", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{filename}.pdf", bbox_inches="tight")
    plt.close()


def load_results():
    single = pd.read_csv(SINGLE_CSV).sort_values("target_rps")
    hpa = pd.read_csv(HPA_CSV).sort_values("target_rps")
    elasticity = pd.read_csv(ELASTICITY_CSV).sort_values("timestamp_utc")

    return single, hpa, elasticity


def plot_execution_time(single: pd.DataFrame, hpa: pd.DataFrame) -> None:
    """
    Average end-to-end request latency.

    Lower values are better.
    """
    plt.figure(figsize=(8, 5))

    plt.plot(
        single["target_rps"],
        single["avg_latency_s"],
        marker="o",
        linewidth=2,
        label="Single instance",
    )

    plt.plot(
        hpa["target_rps"],
        hpa["avg_latency_s"],
        marker="s",
        linewidth=2,
        label="HPA enabled",
    )

    plt.xlabel("Target requests per second (RPS)")
    plt.ylabel("Average latency (seconds)")
    plt.title("AWS Execution Time vs Requested Load")
    plt.xticks(sorted(set(single["target_rps"]) | set(hpa["target_rps"])))
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_plot("aws_execution_time")


def plot_throughput(single: pd.DataFrame, hpa: pd.DataFrame) -> None:
    """
    Achieved successful throughput compared with requested RPS.
    """
    plt.figure(figsize=(8, 5))

    plt.plot(
        single["target_rps"],
        single["throughput_rps"],
        marker="o",
        linewidth=2,
        label="Single instance",
    )

    plt.plot(
        hpa["target_rps"],
        hpa["throughput_rps"],
        marker="s",
        linewidth=2,
        label="HPA enabled",
    )

    max_rps = max(single["target_rps"].max(), hpa["target_rps"].max())

    
    plt.plot(
        [0, max_rps],
        [0, max_rps],
        linestyle="--",
        linewidth=1.5,
        label="Ideal throughput",
    )

    plt.xlabel("Target requests per second (RPS)")
    plt.ylabel("Successful throughput (RPS)")
    plt.title("AWS Throughput vs Requested Load")
    plt.xticks(sorted(set(single["target_rps"]) | set(hpa["target_rps"])))
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_plot("aws_throughput")


def plot_speedup(single: pd.DataFrame, hpa: pd.DataFrame) -> None:
    """
    Speedup = single-instance average latency / HPA average latency.

    A value:
        > 1 means HPA is faster
        = 1 means approximately equal
        < 1 means the single-instance result is faster

    Rows with zero latency are excluded because they normally indicate that
    no successful requests were available from which latency could be measured.
    """
    merged = pd.merge(
        single[
            [
                "target_rps",
                "avg_latency_s",
                "success_rate_percent",
            ]
        ],
        hpa[
            [
                "target_rps",
                "avg_latency_s",
                "success_rate_percent",
            ]
        ],
        on="target_rps",
        suffixes=("_single", "_hpa"),
    )

    valid = merged[
        (merged["avg_latency_s_single"] > 0)
        & (merged["avg_latency_s_hpa"] > 0)
        & (merged["success_rate_percent_single"] > 0)
        & (merged["success_rate_percent_hpa"] > 0)
    ].copy()

    valid["speedup"] = (
        valid["avg_latency_s_single"] / valid["avg_latency_s_hpa"]
    )

    plt.figure(figsize=(8, 5))

    plt.plot(
        valid["target_rps"],
        valid["speedup"],
        marker="o",
        linewidth=2,
        label="Latency speedup",
    )

    plt.axhline(
        y=1,
        linestyle="--",
        linewidth=1.5,
        label="No speedup (1×)",
    )

    plt.xlabel("Target requests per second (RPS)")
    plt.ylabel("Speedup (Single latency / HPA latency)")
    plt.title("AWS HPA Speedup")
    plt.xticks(valid["target_rps"])
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_plot("aws_speedup")


def plot_success_rate(single: pd.DataFrame, hpa: pd.DataFrame) -> None:
    """
    Useful companion plot because latency alone can be misleading when
    a large percentage of requests fail.
    """
    plt.figure(figsize=(8, 5))

    plt.plot(
        single["target_rps"],
        single["success_rate_percent"],
        marker="o",
        linewidth=2,
        label="Single instance",
    )

    plt.plot(
        hpa["target_rps"],
        hpa["success_rate_percent"],
        marker="s",
        linewidth=2,
        label="HPA enabled",
    )

    plt.xlabel("Target requests per second (RPS)")
    plt.ylabel("Successful requests (%)")
    plt.title("AWS Success Rate vs Requested Load")
    plt.xticks(sorted(set(single["target_rps"]) | set(hpa["target_rps"])))
    plt.ylim(0, 105)
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_plot("aws_success_rate")


def plot_elasticity(elasticity: pd.DataFrame) -> None:
    """
    Shows whether the system scales up for the high-load phase and
    recovers when load returns to the low level.
    """
    data = elasticity.reset_index(drop=True).copy()

    stage_labels = []
    low_counter = 0

    for _, row in data.iterrows():
        if "high" in str(row["mode"]).lower():
            stage_labels.append(f"High\n{int(row['target_rps'])} RPS")
        else:
            low_counter += 1
            if low_counter == 1:
                stage_labels.append(f"Low before\n{int(row['target_rps'])} RPS")
            else:
                stage_labels.append(f"Low after\n{int(row['target_rps'])} RPS")

    x = range(len(data))

    plt.figure(figsize=(8, 5))

    plt.plot(
        x,
        data["target_rps"],
        marker="o",
        linewidth=2,
        label="Target RPS",
    )

    plt.plot(
        x,
        data["throughput_rps"],
        marker="s",
        linewidth=2,
        label="Achieved throughput",
    )

    plt.xlabel("Elasticity test phase")
    plt.ylabel("Requests per second (RPS)")
    plt.title("AWS Elasticity: Low → High → Low Load")
    plt.xticks(list(x), stage_labels)
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_plot("aws_elasticity")


def main() -> None:
    single, hpa, elasticity = load_results()

    plot_execution_time(single, hpa)
    plot_throughput(single, hpa)
    plot_speedup(single, hpa)
    plot_success_rate(single, hpa)
    plot_elasticity(elasticity)

    print(f"Plots created in: {OUTPUT_DIR}")
    print("Generated:")
    print("  - aws_execution_time.png / .pdf")
    print("  - aws_throughput.png / .pdf")
    print("  - aws_speedup.png / .pdf")
    print("  - aws_success_rate.png / .pdf")
    print("  - aws_elasticity.png / .pdf")


if __name__ == "__main__":
    main()
