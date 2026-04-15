import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from scipy.optimize import curve_fit

# -------------------------------
# 1. INPUT ln(M) DATA (your values)
# -------------------------------
lnM = np.array([
3.7576,4.4516,4.8584,5.1459,5.3695,5.5522,5.6975,5.8246,5.9376,6.0388,
6.1308,6.2151,6.2927,6.3648,6.432,6.4951,6.5529,6.6073,6.6589,6.708,
6.7548,6.7996,6.8424,6.8834,6.9237,6.9627,7.0006,7.0375,7.0732,7.1079,
7.1415,7.1741,7.2057,7.2362,7.2656,7.2941,7.3218,7.3487,7.3747,7.4,
7.4245,7.4484,7.4717,7.4943,7.5163,7.5379,7.559,7.5798,7.6002,7.6204,
7.6403,7.6599,7.6793,7.6984,7.7172,7.7356,7.7536,7.7714,7.7888,7.8059,
7.8227,7.8392,7.8554,7.8713,7.8868,7.902,7.9169,7.9316,7.9461,7.9603,
7.9744,7.9884,8.002,8.0155,8.0289,8.0422,8.0554,8.0685,8.0815,8.0944,
8.107,8.1195,8.1317,8.1437,8.1554,8.1669,8.1782,8.1894,8.2004,8.2113,
8.2221,8.2328,8.2434,8.254,8.2645,8.275,8.2853,8.2956,8.3057,8.3157,
8.3256,8.3354,8.345,8.3545,8.3639,8.3731,8.3823,8.3913,8.4002,8.4091,
8.4179,8.4268,8.4355,8.4442,8.4528,8.4613,8.4697,8.478,8.4862,8.4943,
8.5023,8.5103,8.5181,8.5258,8.5335,8.5411,8.5486,8.5561,8.5635,8.5708,
8.5781,8.5853,8.5926,8.5998,8.6071,8.6143,8.6215,8.6287,8.6358,8.6429,
8.6499,8.6568,8.6636,8.6704,8.6771,8.6838,8.6904,8.6969,8.7034,8.7099,
8.7162,8.7226,8.7289,8.7353,8.7416,8.7479,8.7542,8.7605,8.7667,8.7729,
8.779,8.785,8.791,8.7969,8.8028,8.8086,8.8144,8.8201,8.8258,8.8314,
8.8371,8.8426,8.8482,8.8538
])

# -------------------------------
# 2. CONVERT ln(M) → M
# -------------------------------
M = np.exp(lnM)

# -------------------------------
# 3. PICK 1, 3, 7 DAY INDICES
# -------------------------------
i1 = 23    # 1 day
i3 = 71    # 3 days
i7 = 167   # 7 days

lnM_data = np.array([lnM[i1], lnM[i3], lnM[i7]]).reshape(-1,1)
M_data = np.array([M[i1], M[i3], M[i7]])

# -------------------------------
# 4. INPUT COMPRESSIVE STRENGTH
# -------------------------------
fc_data = np.array([14.9, 27.3, 29.02])  # <-- replace 32.0 with your 7-day value

# -------------------------------
# 5. LINEAR MODEL: fc = a + b ln(M)
# -------------------------------
lin_model = LinearRegression()
lin_model.fit(lnM_data, fc_data)

a = lin_model.intercept_
b = lin_model.coef_[0]

print("\n--- Linear Model ---")
print("a =", a)
print("b =", b)

# -------------------------------
# 6. NONLINEAR MODEL: fc = A(1 - exp(-kM))
# -------------------------------
def nonlinear_model(M, A, k):
    return A * (1 - np.exp(-k * M))

params, _ = curve_fit(nonlinear_model, M_data, fc_data, p0=[40, 0.0001])
A, k = params

print("\n--- Nonlinear Model ---")
print("A =", A)
print("k =", k)

# -------------------------------
# 7. PLOTTING
# -------------------------------
M_range = np.linspace(min(M), max(M)*2.5, 200)

fc_linear = a + b * np.log(M_range)
fc_nonlinear = nonlinear_model(M_range, A, k)

plt.figure()

# Data points
plt.scatter(M_data, fc_data)

# Curves
plt.plot(M_range, fc_linear, label="Linear Model")
plt.plot(M_range, fc_nonlinear, label="Nonlinear Model")

plt.xlabel("Maturity (M)")
plt.ylabel("Compressive Strength (MPa)")
plt.title("Strength vs Maturity")

plt.legend()
plt.grid()

plt.show()
