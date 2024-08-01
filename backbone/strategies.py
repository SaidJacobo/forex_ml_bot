import numpy as np

def sma_bband_adx(prices_with_indicators, window):
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


def sma_bband_adx_sell(prices_with_indicators, window):
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


def bband_rsi_sell(prices_with_indicators, window):
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


def bband_sell(prices_with_indicators, window):
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


def bband_rsi_sell(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), -1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), 1, df['bband_flag']) 

    df['rsi_flag'] = 0
    df['rsi_flag'] = np.where((df['rsi'] > 70), -1, df['rsi_flag']) 
    df['rsi_flag'] = np.where((df['rsi'] < 30), 1, df['rsi_flag']) 

    
    df['bband_distance_flag'] = 0
    df['bband_distance_flag'] = np.where((df['distance_between_bbands'] > 80), 1, df['bband_distance_flag']) 

    # Bband Flag
    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).all() else 0, raw=True)
    df['rsi_flag_negative_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).all() else 0, raw=True)
    df['bband_distance_flag_window'] = df['bband_distance_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).all() else 0, raw=True)

    amount_conditions = 4

    short_signals = (
        (df['bband_flag_negative_window'].shift(1) == 1).astype(int) +
        (df['rsi_flag_negative_window'] == 1).astype(int) +
        
        (df['Close'] < df['Open']).astype(int) +
        # (df['Close'].shift(1) < df['upper_bband'].shift(1)).astype(int) +
        
        (df['bband_distance_flag_window'] == 1).astype(int)
    ) >= amount_conditions

    df.loc[short_signals, 'side'] = -1

    df.dropna(inplace=True)
    return df


def bband_doub_sell(prices_with_indicators, window):
    df = prices_with_indicators.copy()
    
    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), -1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), 1, df['bband_flag']) 

    df['rsi_flag'] = 0
    df['rsi_flag'] = np.where((df['rsi'] > 70), -1, df['rsi_flag']) 
    df['rsi_flag'] = np.where((df['rsi'] < 30), 1, df['rsi_flag']) 

    df['bband_distance_flag'] = 0
    df['bband_distance_flag'] = np.where((df['distance_between_bbands'] > 80), 1, df['bband_distance_flag']) 

    # Bband Flag
    df['bband_flag_negative_window'] = df['bband_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).all() else 0, raw=True)
    df['rsi_flag_negative_window'] = df['rsi_flag'].rolling(window=window).apply(lambda x: 1 if (x == -1).all() else 0, raw=True)
    df['bband_distance_flag_window'] = df['bband_distance_flag'].rolling(window=window).apply(lambda x: 1 if (x == 1).all() else 0, raw=True)

    amount_conditions = 4

    short_signals_1 = (
        (df['bband_flag_negative_window'].shift(1) == 1).astype(int) +
        (df['rsi_flag_negative_window'] == 1).astype(int) +
        (df['Close'] < df['Open']).astype(int) +
        (df['bband_distance_flag_window'] == 1).astype(int)
    ) >= amount_conditions


    short_signals_2 = (
        (df['bband_flag_negative_window'].shift(2) == 1).astype(int) +
        (df['Close'] < df['upper_bband']).astype(int) +
        (df['Close'].shift(1) < df['upper_bband'].shift(1)).astype(int) +
        (df['bband_distance_flag_window'] == 1).astype(int)
    ) >= amount_conditions


    df.loc[short_signals_1, 'side'] = -1
    df.loc[short_signals_2, 'side'] = -1

    df.dropna(inplace=True)
    return df

def aroon(prices_with_indicators, window):
    adx_value = 25
    aroon_value = 40

    df = prices_with_indicators.copy()

    short_signals = (
        ((df['aroon'] >= aroon_value)) &
        (df['supertrend'] == -1) &
        ((df['adx'] > adx_value)) 
        & (
            (df['engulfing'] == -100) 
            | (df['hanging_man'] == -100)
            | (df['shooting_star'] == -100)
            | (df['marubozu'] == -100)
            | (df['evening_star'] == -100)
            | (df['three_black_crows'] == -100)
        )
        
    )

    long_signals = (
        ((df['aroon'] <= -aroon_value)) &
        (df['supertrend'] == 1) &
        ((df['adx'] > adx_value)) 
        & (
            (df['engulfing'] == 100) 
            | (df['hammer'] == 100)
            | (df['inverted_hammer'] == 100)
            | (df['marubozu'] == 100)
            | (df['morning_star'] == 100)
            | (df['three_white_soldiers'] == 100)
            
        )
        
    )

    df.loc[short_signals, 'side'] = -1
    df.loc[long_signals, 'side'] = 1

    df.dropna(inplace=True)
    return df


def smi_adx(prices_with_indicators, window):
    
    df = prices_with_indicators.copy()
    
    long_signals = (
        (df['SQZ_OFF'] == 1) 
        & (df['SQZ_OFF'].shift(1) == 0)  
        & (df['SQZ'] > 0)  
        & (df['adx'] > 20) 
        & (df['supertrend'] == 1) 
    )

    short_signals = (
        (df['SQZ_OFF'] == 1) 
        & (df['SQZ_OFF'].shift(1) == 0) 
        & (df['SQZ'] < 0) 
        & (df['adx'] > 20)
        & (df['supertrend'] == -1) 

    )
    
    df.loc[short_signals, 'side'] = -1
    df.loc[long_signals, 'side'] = 1

    df.dropna(inplace=True)
    return df