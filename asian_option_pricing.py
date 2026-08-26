import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. MODEL PARAMETERS
# ============================================================

MU = 0.10          # Real-world drift
SIGMA = 0.20       # Volatility
R = 0.05           # Risk-free rate
S0 = 100.0         # Initial asset price
T = 0.5            # 6 months
N = 126            # Daily monitoring over 6 months
DT = T / N

M_PATHS = 10       # Paths for visualization
M_MC = 100_000     # Monte Carlo simulations

STRIKES = [90, 105, 110]

np.random.seed(42)


# ============================================================
# 2. OUTPUT DIRECTORIES
# ============================================================

RESULTS_DIR = "results"
OUTPUTS_DIR = "outputs"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


# ============================================================
# 3. GBM SIMULATION
# ============================================================

def simulate_gbm_paths(S0, drift, sigma, T, N, M, Z=None):
    """
    Simulate Geometric Brownian Motion paths.

    dS = drift*S*dt + sigma*S*dW

    If Z is supplied, the same random numbers can be reused
    for fair comparison between simulation methods.
    """

    dt = T / N

    if Z is None:
        Z = np.random.standard_normal((N, M))

    paths = np.zeros((N + 1, M))
    paths[0] = S0

    for t in range(1, N + 1):
        paths[t] = (
            paths[t - 1]
            * np.exp(
                (drift - 0.5 * sigma**2) * dt
                + sigma * np.sqrt(dt) * Z[t - 1]
            )
        )

    return paths


# ============================================================
# 4. REAL-WORLD AND RISK-NEUTRAL GBM PATHS
# ============================================================

# Same random shocks are used so that the comparison
# isolates the effect of the drift.

Z = np.random.standard_normal((N, M_PATHS))

real_paths = simulate_gbm_paths(
    S0,
    MU,
    SIGMA,
    T,
    N,
    M_PATHS,
    Z
)

rn_paths = simulate_gbm_paths(
    S0,
    R,
    SIGMA,
    T,
    N,
    M_PATHS,
    Z
)

time_grid = np.linspace(0, T, N + 1)


# ============================================================
# 5. PLOT GBM PATHS
# ============================================================

plt.figure(figsize=(9, 6))

for i in range(M_PATHS):
    plt.plot(
        time_grid,
        real_paths[:, i],
        alpha=0.8
    )

plt.xlabel("Time (Years)")
plt.ylabel("Asset Price")
plt.title("GBM Simulation - Real-World Measure")
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "01_gbm_real_world.png"
    ),
    dpi=150
)

plt.show()


plt.figure(figsize=(9, 6))

for i in range(M_PATHS):
    plt.plot(
        time_grid,
        rn_paths[:, i],
        alpha=0.8
    )

plt.xlabel("Time (Years)")
plt.ylabel("Asset Price")
plt.title("GBM Simulation - Risk-Neutral Measure")
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "02_gbm_risk_neutral.png"
    ),
    dpi=150
)

plt.show()


# ============================================================
# 6. STANDARD MONTE CARLO ASIAN OPTION PRICING
# ============================================================

def price_asian_mc(
    S0,
    K,
    r,
    sigma,
    T,
    N,
    M,
    random_seed=None
):
    """
    Price an arithmetic Asian call and put using
    standard Monte Carlo simulation.

    The arithmetic average is computed using the
    daily monitoring prices excluding S0.
    """

    if random_seed is not None:
        rng = np.random.default_rng(random_seed)
        Z = rng.standard_normal((N, M))
    else:
        Z = np.random.standard_normal((N, M))

    paths = simulate_gbm_paths(
        S0,
        r,
        sigma,
        T,
        N,
        M,
        Z
    )

    # Arithmetic average excluding initial price S0
    averages = np.mean(
        paths[1:],
        axis=0
    )

    call_payoffs = np.maximum(
        averages - K,
        0
    )

    put_payoffs = np.maximum(
        K - averages,
        0
    )

    discount = np.exp(-r * T)

    call_price = (
        discount
        * np.mean(call_payoffs)
    )

    put_price = (
        discount
        * np.mean(put_payoffs)
    )

    call_se = (
        discount
        * np.std(
            call_payoffs,
            ddof=1
        )
        / np.sqrt(M)
    )

    put_se = (
        discount
        * np.std(
            put_payoffs,
            ddof=1
        )
        / np.sqrt(M)
    )

    call_ci = (
        call_price - 1.96 * call_se,
        call_price + 1.96 * call_se
    )

    put_ci = (
        put_price - 1.96 * put_se,
        put_price + 1.96 * put_se
    )

    return (
        call_price,
        call_se,
        call_ci,
        put_price,
        put_se,
        put_ci
    )


# ============================================================
# 7. PRICE OPTIONS FOR DIFFERENT STRIKES
# ============================================================

results_mc = []

for K in STRIKES:

    (
        call_price,
        call_se,
        call_ci,
        put_price,
        put_se,
        put_ci
    ) = price_asian_mc(
        S0,
        K,
        R,
        SIGMA,
        T,
        N,
        M_MC,
        random_seed=42
    )

    results_mc.append({
        "Strike": K,
        "Call Price": call_price,
        "Call SE": call_se,
        "Call 95% CI":
            f"[{call_ci[0]:.4f}, {call_ci[1]:.4f}]",
        "Put Price": put_price,
        "Put SE": put_se,
        "Put 95% CI":
            f"[{put_ci[0]:.4f}, {put_ci[1]:.4f}]"
    })


df_mc = pd.DataFrame(results_mc)

print("\n" + "=" * 80)
print("STANDARD MONTE CARLO ASIAN OPTION PRICING")
print("=" * 80)

print(
    df_mc.to_string(
        index=False
    )
)


# Save pricing results
df_mc.to_csv(
    os.path.join(
        OUTPUTS_DIR,
        "pricing_results.csv"
    ),
    index=False
)


# ============================================================
# 8. PLOT OPTION PRICE VS STRIKE
# ============================================================

plt.figure(figsize=(9, 6))

plt.plot(
    df_mc["Strike"],
    df_mc["Call Price"],
    marker="o",
    label="Asian Call"
)

plt.plot(
    df_mc["Strike"],
    df_mc["Put Price"],
    marker="s",
    label="Asian Put"
)

plt.xlabel("Strike Price")
plt.ylabel("Option Price")
plt.title("Asian Option Prices vs Strike")
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "03_option_prices_vs_strike.png"
    ),
    dpi=150
)

plt.show()


# ============================================================
# 9. SENSITIVITY ANALYSIS
# ============================================================

K_SENS = 105

sensitivity_results = []


# ------------------------------------------------------------
# Sensitivity to initial asset price
# ------------------------------------------------------------

for s0_value in [90, 100, 110]:

    (
        call_price,
        _,
        _,
        put_price,
        _,
        _
    ) = price_asian_mc(
        s0_value,
        K_SENS,
        R,
        SIGMA,
        T,
        N,
        50_000,
        random_seed=100
    )

    sensitivity_results.append({
        "Variable": "S0",
        "Value": s0_value,
        "Call Price": call_price,
        "Put Price": put_price
    })


# ------------------------------------------------------------
# Sensitivity to volatility
# ------------------------------------------------------------

for sigma_value in [0.10, 0.20, 0.30]:

    (
        call_price,
        _,
        _,
        put_price,
        _,
        _
    ) = price_asian_mc(
        S0,
        K_SENS,
        R,
        sigma_value,
        T,
        N,
        50_000,
        random_seed=100
    )

    sensitivity_results.append({
        "Variable": "Sigma",
        "Value": sigma_value,
        "Call Price": call_price,
        "Put Price": put_price
    })


df_sensitivity = pd.DataFrame(
    sensitivity_results
)

print("\n" + "=" * 80)
print("SENSITIVITY ANALYSIS (K = 105)")
print("=" * 80)

print(
    df_sensitivity.to_string(
        index=False
    )
)


# Save sensitivity results
df_sensitivity.to_csv(
    os.path.join(
        OUTPUTS_DIR,
        "sensitivity_results.csv"
    ),
    index=False
)


# ============================================================
# 10. SENSITIVITY PLOTS
# ============================================================

s0_data = df_sensitivity[
    df_sensitivity["Variable"] == "S0"
]


# ------------------------------------------------------------
# Sensitivity to S0
# ------------------------------------------------------------

plt.figure(figsize=(9, 6))

plt.plot(
    s0_data["Value"],
    s0_data["Call Price"],
    marker="o",
    label="Call"
)

plt.plot(
    s0_data["Value"],
    s0_data["Put Price"],
    marker="s",
    label="Put"
)

plt.xlabel("Initial Asset Price S0")
plt.ylabel("Option Price")
plt.title("Sensitivity to Initial Asset Price")
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "04_sensitivity_S0.png"
    ),
    dpi=150
)

plt.show()


# ------------------------------------------------------------
# Sensitivity to volatility
# ------------------------------------------------------------

sigma_data = df_sensitivity[
    df_sensitivity["Variable"] == "Sigma"
]

plt.figure(figsize=(9, 6))

plt.plot(
    sigma_data["Value"],
    sigma_data["Call Price"],
    marker="o",
    label="Call"
)

plt.plot(
    sigma_data["Value"],
    sigma_data["Put Price"],
    marker="s",
    label="Put"
)

plt.xlabel("Volatility")
plt.ylabel("Option Price")
plt.title("Sensitivity to Volatility")
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "05_sensitivity_volatility.png"
    ),
    dpi=150
)

plt.show()


# ============================================================
# 11. ANTITHETIC VARIATES
# ============================================================

def price_asian_antithetic(
    S0,
    K,
    r,
    sigma,
    T,
    N,
    M,
    seed=42
):
    """
    Arithmetic Asian option pricing using
    Antithetic Variates.

    For every random path generated using Z,
    an antithetic path using -Z is generated.

    The paired payoff average is used as the estimator.
    """

    if M % 2 != 0:
        raise ValueError(
            "M must be even for antithetic variates."
        )

    rng = np.random.default_rng(seed)

    M_half = M // 2

    Z = rng.standard_normal(
        (N, M_half)
    )

    paths_plus = simulate_gbm_paths(
        S0,
        r,
        sigma,
        T,
        N,
        M_half,
        Z
    )

    paths_minus = simulate_gbm_paths(
        S0,
        r,
        sigma,
        T,
        N,
        M_half,
        -Z
    )

    avg_plus = np.mean(
        paths_plus[1:],
        axis=0
    )

    avg_minus = np.mean(
        paths_minus[1:],
        axis=0
    )

    call_plus = np.maximum(
        avg_plus - K,
        0
    )

    call_minus = np.maximum(
        avg_minus - K,
        0
    )

    put_plus = np.maximum(
        K - avg_plus,
        0
    )

    put_minus = np.maximum(
        K - avg_minus,
        0
    )

    # Antithetic paired estimators
    call_pair = 0.5 * (
        call_plus + call_minus
    )

    put_pair = 0.5 * (
        put_plus + put_minus
    )

    discount = np.exp(-r * T)

    call_price = (
        discount
        * np.mean(call_pair)
    )

    put_price = (
        discount
        * np.mean(put_pair)
    )

    call_se = (
        discount
        * np.std(
            call_pair,
            ddof=1
        )
        / np.sqrt(M_half)
    )

    put_se = (
        discount
        * np.std(
            put_pair,
            ddof=1
        )
        / np.sqrt(M_half)
    )

    # 95% confidence intervals
    call_ci = (
        call_price - 1.96 * call_se,
        call_price + 1.96 * call_se
    )

    put_ci = (
        put_price - 1.96 * put_se,
        put_price + 1.96 * put_se
    )

    return (
        call_price,
        call_se,
        call_ci,
        put_price,
        put_se,
        put_ci
    )


# ============================================================
# 12. STANDARD MC VS ANTITHETIC VARIATES
# ============================================================

comparison_results = []

for K in STRIKES:

    # --------------------------------------------------------
    # Standard Monte Carlo
    # --------------------------------------------------------

    (
        call_std,
        call_se_std,
        call_ci_std,
        put_std,
        put_se_std,
        put_ci_std
    ) = price_asian_mc(
        S0,
        K,
        R,
        SIGMA,
        T,
        N,
        M_MC,
        random_seed=42
    )


    # --------------------------------------------------------
    # Antithetic Variates
    # --------------------------------------------------------

    (
        call_av,
        call_se_av,
        call_ci_av,
        put_av,
        put_se_av,
        put_ci_av
    ) = price_asian_antithetic(
        S0,
        K,
        R,
        SIGMA,
        T,
        N,
        M_MC,
        seed=42
    )


    # --------------------------------------------------------
    # Variance reduction
    # --------------------------------------------------------

    call_variance_reduction = (
        1
        - (call_se_av ** 2 / call_se_std ** 2)
    ) * 100

    put_variance_reduction = (
        1
        - (put_se_av ** 2 / put_se_std ** 2)
    ) * 100


    comparison_results.append({

        "Strike": K,

        "Call MC": call_std,
        "Call AV": call_av,

        "Call SE MC": call_se_std,
        "Call SE AV": call_se_av,

        "Call 95% CI MC":
            f"[{call_ci_std[0]:.4f}, "
            f"{call_ci_std[1]:.4f}]",

        "Call 95% CI AV":
            f"[{call_ci_av[0]:.4f}, "
            f"{call_ci_av[1]:.4f}]",

        "Call Variance Reduction %":
            call_variance_reduction,

        "Put MC": put_std,
        "Put AV": put_av,

        "Put SE MC": put_se_std,
        "Put SE AV": put_se_av,

        "Put 95% CI MC":
            f"[{put_ci_std[0]:.4f}, "
            f"{put_ci_std[1]:.4f}]",

        "Put 95% CI AV":
            f"[{put_ci_av[0]:.4f}, "
            f"{put_ci_av[1]:.4f}]",

        "Put Variance Reduction %":
            put_variance_reduction
    })


df_comparison = pd.DataFrame(
    comparison_results
)

print("\n" + "=" * 80)
print("STANDARD MONTE CARLO VS ANTITHETIC VARIATES")
print("=" * 80)

print(
    df_comparison.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}"
    )
)


# Save variance reduction results
df_comparison.to_csv(
    os.path.join(
        OUTPUTS_DIR,
        "variance_reduction_results.csv"
    ),
    index=False
)


# ============================================================
# 13. STANDARD ERROR COMPARISON
# ============================================================

x = np.arange(len(STRIKES))
width = 0.18


# ------------------------------------------------------------
# Call standard error
# ------------------------------------------------------------

plt.figure(figsize=(9, 6))

plt.bar(
    x - width / 2,
    df_comparison["Call SE MC"],
    width,
    label="Call SE - Standard MC"
)

plt.bar(
    x + width / 2,
    df_comparison["Call SE AV"],
    width,
    label="Call SE - Antithetic"
)

plt.xticks(
    x,
    STRIKES
)

plt.xlabel("Strike Price")
plt.ylabel("Standard Error")
plt.title(
    "Call Monte Carlo Standard Error Comparison"
)

plt.legend()
plt.grid(axis="y")
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "06_call_standard_error_comparison.png"
    ),
    dpi=150
)

plt.show()


# ------------------------------------------------------------
# Put standard error
# ------------------------------------------------------------

plt.figure(figsize=(9, 6))

plt.bar(
    x - width / 2,
    df_comparison["Put SE MC"],
    width,
    label="Put SE - Standard MC"
)

plt.bar(
    x + width / 2,
    df_comparison["Put SE AV"],
    width,
    label="Put SE - Antithetic"
)

plt.xticks(
    x,
    STRIKES
)

plt.xlabel("Strike Price")
plt.ylabel("Standard Error")
plt.title(
    "Put Monte Carlo Standard Error Comparison"
)

plt.legend()
plt.grid(axis="y")
plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULTS_DIR,
        "07_put_standard_error_comparison.png"
    ),
    dpi=150
)

plt.show()


# ============================================================
# 14. FINAL OBSERVATIONS
# ============================================================

print("\n" + "=" * 80)
print("OBSERVATIONS")
print("=" * 80)

print("""
1. Under the real-world measure, the GBM drift is μ = 10%.
   Under the risk-neutral measure, the drift changes to r = 5%.

2. As the strike price increases:
   - Asian call prices generally decrease.
   - Asian put prices generally increase.

3. Increasing the initial asset price generally increases call
   option prices and decreases put option prices.

4. Increasing volatility generally increases the value of both
   call and put options because higher volatility increases the
   dispersion of the average asset price.

5. Antithetic Variates reduce Monte Carlo variance by pairing
   each simulated path generated from Z with a path generated
   from -Z.

6. A lower standard error indicates a more statistically efficient
   Monte Carlo estimator for the same computational budget.

7. The 95% confidence interval provides an estimate of the
   uncertainty associated with the Monte Carlo option price.
""")

print("\nAnalysis completed successfully.")