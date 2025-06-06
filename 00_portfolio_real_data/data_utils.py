import pandas as pd
import numpy as np
from typing import List, Optional, Union, Tuple

def align_time_series_fast(df, fill_method='ffill', fill_value=0):
    """
    Fast align time series data for different symbols without lookahead.
    Uses pivot/groupby method for better performance.
    
    Parameters:
    - df: DataFrame with 'open_time' and 'symbol' columns
    - fill_method: Method to fill missing values ('ffill' for forward fill)
    - fill_value: Value to use when there are no previous values (default: 0)
    
    Returns:
    - DataFrame with aligned time series
    """
    # Make sure open_time is datetime
    df['open_time'] = pd.to_datetime(df['open_time'])
    
    # Create a multi-index from all combinations of time and symbol
    all_times = df['open_time'].unique()
    all_symbols = df['symbol'].unique()
    
    # Create a complete index
    idx = pd.MultiIndex.from_product([all_times, all_symbols], names=['open_time', 'symbol'])
    
    # Set multi-index and reindex to get all combinations
    df_indexed = df.set_index(['open_time', 'symbol'])
    aligned_df = df_indexed.reindex(idx)
    
    # Group by symbol and apply forward fill
    if fill_method == 'ffill':
        aligned_df = aligned_df.groupby(level='symbol').ffill()
    
    # Fill remaining NaN with fill_value
    aligned_df = aligned_df.fillna(fill_value)
    
    # Reset index
    aligned_df = aligned_df.reset_index()
    
    return aligned_df.sort_values(['symbol', 'open_time']).reset_index(drop=True)


#efficient version using vectorized operations across all columns at once
"""
def minmaxscaler_by_symbol(df, feature_range=(-1, 1), target_columns=None, group_by_column='symbol'):
    
    Ultra-efficient MinMaxScaler using vectorized groupby operations
    
    Parameters:
    - df: DataFrame to scale
    - feature_range: tuple of (min, max) to scale data to, default (-1, 1)
    - target_columns: list of specific columns to scale
    - group_by_column: column to group by for scaling
    
    Returns:
    - Scaled DataFrame
    # Determine columns to scale
    if target_columns is None:
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        target_columns = [col for col in numeric_columns if col not in ['open_time', group_by_column]]
    
    # Create a copy
    scaled_df = df.copy()
    
    # Get feature range parameters
    feature_min, feature_max = feature_range
    feature_span = feature_max - feature_min
    
    # Get the subset of columns to scale
    data_to_scale = df[target_columns]
    
    # Perform vectorized groupby operations
    grouped = df.groupby(group_by_column)
    
    # Calculate min and max for all columns at once
    group_mins = grouped[target_columns].transform('min')
    group_maxs = grouped[target_columns].transform('max')
    group_ranges = group_maxs - group_mins
    
    # Apply scaling formula vectorized across all columns
    # Handle division by zero for constant values
    scaled_values = np.where(
        group_ranges == 0,
        feature_min,
        (data_to_scale - group_mins) / group_ranges * feature_span + feature_min
    )
    
    # Assign scaled values back to the DataFrame
    scaled_df[target_columns] = scaled_values
    
    return scaled_df
"""



class GroupMinMaxScaler:
    """
    Ultra-efficient MinMaxScaler using vectorized groupby operations
    
    Parameters:
    - df: DataFrame to scale
    - feature_range: tuple of (min, max) to scale data to, default (-1, 1)
    - target_columns: list of specific columns to scale
    - group_by_column: column to group by for scaling
    """
    def __init__(self, feature_range=(-1, 1), target_columns=None, group_by_column='symbol'):
        self.feature_min, self.feature_max = feature_range
        self.feature_span = self.feature_max - self.feature_min
        self.target_columns = target_columns
        self.group_by = group_by_column
        # 下面两个在 fit() 时会被赋值
        self._mins = None    # DataFrame: index=symbol, cols=target_columns
        self._ranges = None  # DataFrame: index=symbol, cols=target_columns

    def fit(self, df):
        # 自动选列
        if self.target_columns is None:
            numeric = df.select_dtypes(include=[np.number]).columns.tolist()
            self.target_columns = [c for c in numeric if c not in [self.group_by]]
        # 计算每组的 min/max/range
        grp = df.groupby(self.group_by)[self.target_columns]
        self._mins   = grp.min()
        self._maxs   = grp.max()
        self._ranges = self._maxs - self._mins
        return self

    def transform(self, df):
        # 先把对应 symbol 的 mins 和 ranges merge 进来
        # Merge mins
        mins = (
            df[[self.group_by]]
            .merge(self._mins, left_on=self.group_by, right_index=True, how='left')
            .set_index(df.index).fillna(self.feature_min)
        )
        ranges = (
            df[[self.group_by]]
            .merge(self._ranges, left_on=self.group_by, right_index=True, how='left')
            .set_index(df.index).fillna(self.feature_span)
        )

        scaled = df.copy()
        data = df[self.target_columns]

        # 公式：(x - min) / range * span + feature_min, 对 range=0 的列直接赋 value=feature_min
        scaled_vals = (data - mins[self.target_columns]) \
                      .divide(ranges[self.target_columns].replace(0, np.nan)) \
                      .multiply(self.feature_span) \
                      .add(self.feature_min) \
                      .fillna(self.feature_min)

        scaled[self.target_columns] = scaled_vals
        return scaled

    def fit_transform(self, df):
        return self.fit(df).transform(df)




def pivot_features_and_costs(
    df: pd.DataFrame,
    y_col: str,
    x_cols: List[str]
) -> Tuple[np.ndarray, np.ndarray, List[pd.Timestamp], List[str]]:
    """
    Pivot DataFrame into feature tensor and cost matrix.

    Returns
    -------
    features : np.ndarray, shape (T, N, k)
    costs    : np.ndarray, shape (T, N)
    times    : list of T timestamps
    symbols  : list of N symbols
    """
    # 检查一下重复值
    duplicates = df.groupby(['open_time', 'symbol']).size()
    if (duplicates > 1).any():
        print("Warning: Found duplicate (time, symbol) pairs")
        print("Duplicates sample:")
        print(duplicates[duplicates > 1].head())
    
    # Pivot cost (target) matrix
    cost_pivot = df.pivot_table(
        values=y_col,
        index="open_time",
        columns="symbol",
        aggfunc="first"
    )
    # Sort and fill missing
    cost_pivot = cost_pivot.sort_index().fillna(0)
    unique_times = cost_pivot.index.tolist()
    unique_symbols = cost_pivot.columns.tolist()
    costs = cost_pivot.values

    # Pivot features and stack
    mats = []
    for x in x_cols:
        mat = df.pivot_table(
            values=x,
            index="open_time",
            columns="symbol",
            aggfunc="first"
        )
        mat = mat.sort_index().reindex(columns=unique_symbols).fillna(0)
        mats.append(mat.values)

    features = np.stack(mats, axis=2)
    print(f"Data shape: features {features.shape}, costs {costs.shape}")

    return features, costs, unique_times, unique_symbols
