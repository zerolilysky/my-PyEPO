import torch
import numpy as np
import os


#############################################################################
# COST & FEATURE COLUMNS
#############################################################################
Y_COL = 'return_30min'  
X_COLS = ['open', 'high', 'low', 'close', 'volume','count']

#############################################################################
# FILE PATHS
#############################################################################
ROOT_PATH = "/Users/tarothousand/Desktop/EndToEnd/my-PyEPO/00_portfolio_real_data"
RAW_DATA_PATH = os.path.join(ROOT_PATH, "perp_futures_klines")
PROCESSED_DATA_PATH = os.path.join(ROOT_PATH, "processed_crypto_data.csv")
ALIGNED_CRYPTO_DATA_PATH = os.path.join(ROOT_PATH, "aligned_crypto_data.parquet")
OPTDATA_DIR = "./data"
OPTDATA_NAME = "crypto_data"
DATASET_DICT_PATH = os.path.join(ROOT_PATH, "large_market_neutral_dataset.npz")

#############################################################################
# OPT_DATASET PRECOMPUTATION
#############################################################################
LOOKBACK = 5
PRECOMPUTE_BATCH_SIZE = 500
PADDING_METHOD = "zero"


#############################################################################
# MARKET NEUTRAL MODEL
#############################################################################
N = 13  # Number of assets, updated from data
A = np.ones((1, N))
b = np.array([1.0])
l = np.zeros(N)
u = np.zeros(N) + 1e6
M = np.random.randn(N, N) # Generate random positive definite covariance matrix
COV_MATRIX = M.T @ M + np.eye(N) * 1e-3

# Risk and constraint parameters
RISK_F     = np.random.randn(N)
RISK_ABS   = 1.5
SINGLE_ABS = 0.1
L1_ABS     = 1.0
SIGMA_ABS  = 2.5


#############################################################################
# DEVICE
#############################################################################
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")
print(f"Using device: {DEVICE}")
# Print extra info
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    torch.cuda.empty_cache()
elif DEVICE.type == "mps":
    print("Using Apple Silicon GPU via Metal Performance Shaders (MPS)")
    
    
#############################################################################
# NEURAL NETWORK PARAMETERS
#############################################################################
K = 6
HIDDEN_DIM = 32
LSTM_HIDDEN_DIM = 64
DROPOUT_RATE = 0.0

NUM_EPOCHS = 5
BATCH_SIZE = 8