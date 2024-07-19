import numpy as np

def sma_bband_adx_stgy(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    # SMA flag
    df['sma_flag'] = 0

    df['sma_flag'] = np.where((df['sma_12'] > df['sma_26']) & (df['sma_12'].shift(1) <= df['sma_26'].shift(1)), 
      1, 
      df['sma_flag']
    )

    df['sma_flag'] = np.where((df['sma_12'] < df['sma_26']) & (df['sma_12'].shift(1) >= df['sma_26'].shift(1)), 
      -1, 
      df['sma_flag']
    )

    # bband flag
    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), 1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), -1, df['bband_flag']) 

    # adx flag
    df['adx_flag'] = 0
    df['adx_flag'] = np.where((df['adx'] > 25), 1, df['adx_flag'])

    df['bband_flag_positive_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True)
    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)

    df['sma_flag_positive_window'] = df['sma_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 
    df['sma_flag_negative_window'] = df['sma_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)
    df['adx_flag_window'] = df['adx_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 

    amount_conditions = 3

    long_signals = (
        (df['bband_flag_positive_window'] == 1).astype(int) +
        (df['sma_flag_positive_window'] == 1).astype(int) +
        (df['adx_flag_window'] == 1).astype(int)
    ) >= amount_conditions

    short_signals = (
        (df['bband_flag_negative_window'] == 1).astype(int) +
        (df['sma_flag_negative_window'] == 1).astype(int) +
        (df['adx_flag_window'] == 1).astype(int)
    ) >= amount_conditions

    df.loc[long_signals, 'side'] = 1
    df.loc[short_signals, 'side'] = -1

    df.dropna(inplace=True)
    return df


def sma_bband_adx_sell_stgy(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    # SMA flag
    df['sma_flag'] = 0

    df['sma_flag'] = np.where((df['sma_12'] < df['sma_26']) & (df['sma_12'].shift(1) >= df['sma_26'].shift(1)), 
      -1, 
      df['sma_flag']
    )

    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), 1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), -1, df['bband_flag']) 
    
    # adx flag
    df['adx_flag'] = 0
    df['adx_flag'] = np.where((df['adx'] > 25), 1, df['adx_flag'])
    
    # Bband Flag
    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)
    df['sma_flag_negative_window'] = df['sma_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)
    df['adx_flag_window'] = df['adx_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 

    amount_conditions = 3

    short_signals = (
        (df['bband_flag_negative_window'] == 1).astype(int) +
        (df['sma_flag_negative_window'] == 1).astype(int) +
        (df['adx_flag_window'] == 1).astype(int)
    ) >= amount_conditions

    df.loc[short_signals, 'side'] = -1

    df.dropna(inplace=True)
    return df


def bband_rsi_sell_stgy(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), 1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), -1, df['bband_flag']) 
    
    df['rsi_flag'] = 0
    df['rsi_flag'] = np.where((df['rsi'] > 70), -1, df['rsi_flag'])
    df['rsi_flag'] = np.where((df['rsi'] < 30), 1, df['rsi_flag'])

    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)
    
    df['rsi_flag_positive_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 
    df['rsi_flag_negative_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)

    amount_conditions = 2

    short_signals = (
        (df['bband_flag_negative_window'] == 1).astype(int) +
        (df['rsi_flag_negative_window'] == 1).astype(int)
    ) >= amount_conditions

    df.loc[short_signals, 'side'] = -1

    df.dropna(inplace=True)
    return df


def bband_sell_stgy(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), -1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), 1, df['bband_flag']) 

    df['bband_distance_flag'] = 0
    df['bband_distance_flag'] = np.where((df['distance_between_bbands'] > 80), 1, df['bband_distance_flag']) 

    # Bband Flag
    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).all() else 0, raw=True)
    df['bband_distance_flag_window'] = df['bband_distance_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).all() else 0, raw=True)

    amount_conditions = 4

    short_signals = (
        (df['bband_flag_negative_window'].shift(2) == 1).astype(int) +
        (df['Close'] < df['upper_bband']).astype(int) +
        (df['Close'].shift(1) < df['upper_bband'].shift(1)).astype(int) +
        (df['bband_distance_flag_window'] == 1).astype(int)
    ) >= amount_conditions

    df.loc[short_signals, 'side'] = -1

    df.dropna(inplace=True)
    return df


# df['macd_flag'] = 0
# df['macd_flag'] = np.where((df['macdhist'].shift(1) < 0) & (df['macdhist'] > 0), 1, df['macd_flag'])
# df['macd_flag'] = np.where((df['macdhist'].shift(1) > 0) & (df['macdhist'] < 0), -1, df['macd_flag'])

# df['rsi_flag'] = 0
# df['rsi_flag'] = np.where((df['rsi'] > 70), -1, df['rsi_flag'])
# df['rsi_flag'] = np.where((df['rsi'] < 30), 1, df['rsi_flag'])

# df['mfi_flag'] = 0
# df['mfi_flag'] = np.where((df['mfi'] > 80), -1, df['mfi_flag'])
# df['mfi_flag'] = np.where((df['mfi'] < 20), 1, df['mfi_flag'])

# window = 5
# df['macd_flag_positive_window'] = df['macd_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True)
# df['macd_flag_negative_window'] = df['macd_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)

# df['rsi_flag_positive_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 
# df['rsi_flag_negative_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)

# df['mfi_flag_positive_window'] = df['mfi_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).any() else 0, raw=True) 
# df['mfi_flag_negative_window'] = df['mfi_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).any() else 0, raw=True)
