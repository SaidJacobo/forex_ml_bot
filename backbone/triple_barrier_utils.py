import numpy as np
import pandas as pd
import multiprocessing as mp
import datetime as dt
import time
import sys
from tqdm import tqdm

class MultiProcessingFunctions:
    """ This static functions in this class enable multi-processing"""
    def __init__(self):
        pass

    @staticmethod
    def lin_parts(num_atoms, num_threads):
        """ This function partitions a list of atoms in subsets (molecules) of equal size.
        An atom is a set of indivisible set of tasks.
        """
        parts = np.linspace(0, num_atoms, min(num_threads, num_atoms) + 1)
        parts = np.ceil(parts).astype(int)
        return parts

    @staticmethod
    def nested_parts(num_atoms, num_threads, upper_triangle=False):
        """ This function enables parallelization of nested loops.
        """
        parts = []
        num_threads_ = min(num_threads, num_atoms)

        for num in range(num_threads_):
            part = 1 + 4 * (parts[-1] ** 2 + parts[-1] + num_atoms * (num_atoms + 1.) / num_threads_)
            part = (-1 + part ** .5) / 2.
            parts.append(part)

        parts = np.round(parts).astype(int)

        if upper_triangle:  # the first rows are heaviest
            parts = np.cumsum(np.diff(parts)[::-1])
            parts = np.append(np.array([0]), parts)
        return parts

    @staticmethod
    def mp_pandas_obj(func, pd_obj, num_threads=24, mp_batches=1, lin_mols=True, **kargs):
        """
        :param func: (string) function to be parallelized
        :param pd_obj: (vector) Element 0, is name of argument used to pass the molecule;
                        Element 1, is the list of atoms to be grouped into a molecule
        :param num_threads: (int) number of threads
        :param mp_batches: (int) number of batches
        :param lin_mols: (bool) Tells if the method should use linear or nested partitioning
        :param kargs: (var args)
        :return: (data frame) of results
        """
        if lin_mols:
            parts = MultiProcessingFunctions.lin_parts(len(pd_obj[1]), num_threads * mp_batches)
        else:
            parts = MultiProcessingFunctions.nested_parts(len(pd_obj[1]), num_threads * mp_batches)

        jobs = []
        for i in range(1, len(parts)):
            job = {pd_obj[0]: pd_obj[1][parts[i - 1]:parts[i]], 'func': func}
            job.update(kargs)
            jobs.append(job)

        if num_threads == 1:
            out = MultiProcessingFunctions.process_jobs_(jobs)
        else:
            out = MultiProcessingFunctions.process_jobs(jobs, num_threads=num_threads)

        if isinstance(out[0], pd.DataFrame):
            df0 = pd.DataFrame()
        elif isinstance(out[0], pd.Series):
            df0 = pd.Series(dtype='float64')
        else:
            return out

        for i in out:
            df0 = pd.concat([df0, i])

        df0 = df0.sort_index()
        return df0

    @staticmethod
    def process_jobs_(jobs):
        """ Run jobs sequentially, for debugging """
        out = []
        for job in jobs:
            out_ = MultiProcessingFunctions.expand_call(job)
            out.append(out_)
        return out

    @staticmethod
    def expand_call(kargs):
        """ Expand the arguments of a callback function, kargs['func'] """
        func = kargs['func']
        del kargs['func']
        out = func(**kargs)
        return out

    @staticmethod
    def report_progress(job_num, num_jobs, time0, task):
        # Report progress as async jobs are completed
        msg = [float(job_num) / num_jobs, (time.time() - time0)/60.]
        msg.append(msg[1] * (1/msg[0] - 1))
        time_stamp = str(dt.datetime.fromtimestamp(time.time()))

        msg = f"{time_stamp} {round(msg[0]*100, 2)}% {task} done after {round(msg[1], 2)} minutes. Remaining {round(msg[2], 2)} minutes."

        if job_num < num_jobs:
            sys.stderr.write(msg + '\r')
        else:
            sys.stderr.write(msg + '\n')

        return

    @staticmethod
    def process_jobs(jobs, task=None, num_threads=24):
        """ Run in parallel. jobs must contain a 'func' callback, for expand_call"""
        if task is None:
            task = jobs[0]['func'].__name__

        pool = mp.Pool(processes=num_threads)
        outputs = pool.imap_unordered(MultiProcessingFunctions.expand_call, jobs)
        out = []
        time0 = time.time()

        # Process async output, report progress
        for i, out_ in enumerate(outputs, 1):
            out.append(out_)
            MultiProcessingFunctions.report_progress(i, len(jobs), time0, task)

        pool.close()
        pool.join()  # this is needed to prevent memory leaks
        return out


def get_daily_vol(close_prices, lookback=100):
    """
    Calculate the daily volatility for dynamic thresholds.
    
    :param close_prices: (pd.DataFrame) DataFrame containing the closing prices with date as the index.
    :param lookback: (int) Lookback period to compute the exponential weighted volatility. Default is 100.
    :return: (pd.Series) Series of daily volatility values.
    """
    print('Calculating daily volatility for dynamic thresholds')

    # Find the index positions of dates which are exactly one day before each date in the index.
    one_day_before_index = close_prices.index.searchsorted(close_prices.index - pd.Timedelta(days=1))

    # Filter out any indices that are non-positive (i.e., that didn't find a valid previous day)
    valid_indices = one_day_before_index[one_day_before_index > 0]

    # Create a Series mapping current date to the previous valid date
    previous_dates = pd.Series(close_prices.index[valid_indices - 1], index=close_prices.index[close_prices.shape[0] - valid_indices.shape[0]:])

    # Calculate daily returns: current closing price / previous day's closing price - 1
    daily_returns = close_prices.loc[previous_dates.index] / close_prices.loc[previous_dates.values].values - 1

    # Calculate the exponentially weighted moving standard deviation of the daily returns
    daily_volatility = daily_returns.ewm(span=lookback).std()

    return daily_volatility

def get_t_events(close_prices, threshold):
    """
    Apply a Symmetric CUSUM filter to identify significant price events.
    
    :param close_prices: (pd.Series) Series of close prices.
    :param threshold: (float) Threshold for cumulative sum; events are triggered when the absolute change exceeds this value.
    :return: (pd.DatetimeIndex) Datetime index vector of timestamps when the events occurred.
    """
    print('Applying Symmetric CUSUM filter.')

    event_timestamps = []
    positive_cumsum = 0
    negative_cumsum = 0

    # Calculate log returns
    log_returns = np.log(close_prices).diff().dropna()

    # Identify event timestamps based on the CUSUM filter
    for timestamp in tqdm(log_returns.index[1:]):
        positive_cumsum = max(0.0, positive_cumsum + log_returns.loc[timestamp])
        negative_cumsum = min(0.0, negative_cumsum + log_returns.loc[timestamp])

        if negative_cumsum < -threshold:
            negative_cumsum = 0
            event_timestamps.append(timestamp)
        elif positive_cumsum > threshold:
            positive_cumsum = 0
            event_timestamps.append(timestamp)

    return pd.DatetimeIndex(event_timestamps)


def add_vertical_barrier(event_timestamps, close_prices, max_holding_days=1):
    """
    Add vertical barriers to events based on a maximum holding period.
    
    :param event_timestamps: (pd.Series) Series of events (timestamps) from the symmetric CUSUM filter.
    :param close_prices: (pd.Series) Series of close prices.
    :param max_holding_days: (int) Maximum number of days a trade can be active.
    :return: (pd.Series) Timestamps of vertical barriers.
    """
    # Calculate the index positions of the vertical barriers
    barrier_indices = close_prices.index.searchsorted(event_timestamps + pd.Timedelta(days=max_holding_days))
    
    # Filter out barriers that go beyond the available price data
    barrier_indices = barrier_indices[barrier_indices < close_prices.shape[0]]
    
    # Create a series with event timestamps as index and barrier timestamps as values
    vertical_barriers = pd.Series(close_prices.index[barrier_indices], index=event_timestamps[:barrier_indices.shape[0]])
    
    return vertical_barriers


def apply_profit_taking_stop_loss(close_prices, events, pt_sl, molecule):
    """
    Apply profit-taking and stop-loss on events.

    :param close_prices: (pd.Series) Close prices.
    :param events: (pd.DataFrame) DataFrame containing event information with columns 't1' and 'trgt'.
    :param pt_sl: (array) Two-element array where the first element is the profit-taking level
                          and the second element is the stop-loss level.
    :param molecule: (list or array) A set of datetime index values for processing.
    :return: (pd.DataFrame) DataFrame with timestamps at which each barrier (profit-taking or stop-loss) was touched.
    """
    # Filter events to include only those in the molecule
    filtered_events = events.loc[molecule]
    output = filtered_events[['t1']].copy(deep=True)

    # Determine the profit-taking and stop-loss levels
    if pt_sl[0] > 0:
        profit_taking_level = pt_sl[0] * filtered_events['trgt']
    else:
        profit_taking_level = pd.Series(index=events.index, dtype='float64')  # NaNs if no profit-taking level

    if pt_sl[1] > 0:
        stop_loss_level = -pt_sl[1] * filtered_events['trgt']
    else:
        stop_loss_level = pd.Series(index=events.index, dtype='float64')  # NaNs if no stop-loss level

    # Iterate through the filtered events to apply profit-taking and stop-loss
    for event_index, event_end_time in filtered_events['t1'].fillna(close_prices.index[-1]).items():
        # Get the path prices for the event duration
        path_prices = close_prices.loc[event_index:event_end_time]
        # Calculate the path returns for the event duration
        path_returns = (path_prices / close_prices.loc[event_index] - 1) * filtered_events.at[event_index, 'side']
        
        # Find the earliest timestamp where stop-loss was reached
        output.loc[event_index, 'sl'] = path_returns[path_returns < stop_loss_level[event_index]].index.min()
        # Find the earliest timestamp where profit-taking was reached
        output.loc[event_index, 'pt'] = path_returns[path_returns > profit_taking_level[event_index]].index.min()

    return output

def get_events(close_prices, event_timestamps, profit_take_stop_loss, target_returns, minimum_return, num_threads,
               vertical_barrier_times=False, bet_side=None):
    """
    Generate events based on the triple barrier method.

    :param close_prices: (pd.Series) Close prices.
    :param event_timestamps: (pd.Series) Timestamps that will seed every triple barrier.
    :param profit_take_stop_loss: (list) Two-element list where the first element indicates the profit-taking level,
                                  and the second element is the stop-loss level. A value of 0 disables the respective barrier.
    :param target_returns: (pd.Series) Values used (in conjunction with profit_take_stop_loss) to determine the width of the barrier.
    :param minimum_return: (float) Minimum target return required for running a triple barrier search.
    :param num_threads: (int) Number of threads to be used concurrently by the function.
    :param vertical_barrier_times: (pd.Series or bool) A pandas series with the timestamps of the vertical barriers. Defaults to False.
    :param bet_side: (pd.Series or None) Side of the bet (long/short) as decided by the primary model. Defaults to None.
    :return: (pd.DataFrame) DataFrame of events with the following columns:
             - events.index: event's start time
             - events['t1']: event's end time
             - events['trgt']: event's target
             - events['side']: (optional) algo's position side
    """

    # 1) Filter target returns to include only those that intersect with event timestamps and are greater than minimum return
    target_returns = target_returns.loc[target_returns.index.intersection(event_timestamps)]
    target_returns = target_returns[target_returns > minimum_return]

    # 2) Get vertical barrier (maximum holding period)
    if vertical_barrier_times is False:
        vertical_barrier_times = pd.Series(pd.NaT, index=event_timestamps)

    # 3) Form events object and apply stop loss on vertical barrier
    if bet_side is None:
        bet_side_ = pd.Series(1.0, index=target_returns.index)
        profit_take_stop_loss_ = [profit_take_stop_loss[0], profit_take_stop_loss[0]]
    else:
        bet_side_ = bet_side.loc[target_returns.index]
        profit_take_stop_loss_ = profit_take_stop_loss[:2]

    events = pd.concat({'t1': vertical_barrier_times, 'trgt': target_returns, 'side': bet_side_}, axis=1)
    events = events.dropna(subset=['trgt'])

    # Apply Triple Barrier Method
    df0 = MultiProcessingFunctions.mp_pandas_obj(func=apply_profit_taking_stop_loss,
                                                 pd_obj=('molecule', events.index),
                                                 num_threads=num_threads,
                                                 close_prices=close_prices,
                                                 events=events,
                                                 pt_sl=profit_take_stop_loss_)

    events['t1'] = df0.dropna(how='all').min(axis=1)  # Use the earliest barrier touch time

    if bet_side is None:
        events = events.drop('side', axis=1)

    return events


def barrier_touched(out_df):
    """
    Label each return according to the event type.

    :param out_df: (pd.DataFrame) DataFrame containing the returns and target.
                   Columns expected: 'ret' for returns, 'trgt' for target.
    :return: (pd.DataFrame) DataFrame containing returns, target, and labels.
             Adds a new column 'bin' with values:
             - 1 for returns exceeding the target (top barrier reached)
             - -1 for returns below the negative target (bottom barrier reached)
             - 0 for returns between -target and target (vertical barrier reached)
    """
    store = []
    for i in np.arange(len(out_df)):
        date_time = out_df.index[i]
        ret = out_df.loc[date_time, 'ret']
        target = out_df.loc[date_time, 'trgt']

        if ret > 0.0 and ret > target:
            # Top barrier reached
            store.append(1)
        elif ret < 0.0 and ret < -target:
            # Bottom barrier reached
            store.append(-1)
        else:
            # Vertical barrier reached
            store.append(0)

    out_df['bin'] = store

    return out_df

def get_bins(triple_barrier_events, close):
    """
    Label each event based on price action or pnl (meta-labeling).

    :param triple_barrier_events: (pd.DataFrame)
                - events.index is event's starttime
                - events['t1'] is event's endtime
                - events['trgt'] is event's target
                - events['side'] (optional) implies the algo's position side
                Case 1: ('side' not in events): bin in (-1, 1) <- label by price action
                Case 2: ('side' in events): bin in (0, 1) <- label by pnl (meta-labeling)
    :param close: (pd.Series) close prices
    :return: (pd.DataFrame) of meta-labeled events
                - 'ret': returns based on price action or pnl
                - 'trgt': target from triple_barrier_events
                - 'bin': labels (-1, 0, 1) based on price action or pnl
                - 'side' (optional): implies the algo's position side

    Meta-labeling logic:
    - If 'side' is in events, multiply 'ret' by 'side' for meta-labeling.
    - Label events based on barrier_touched function.
    - For meta-labeling, label incorrect events with 'bin' = 0.
    """
    # 1) Align prices with their respective events
    events_ = triple_barrier_events.dropna(subset=['t1'])
    prices = events_.index.union(events_['t1'].values)
    prices = prices.drop_duplicates()
    prices = close.reindex(prices, method='bfill')

    # 2) Create out DataFrame
    out_df = pd.DataFrame(index=events_.index)
    # Take the log returns to avoid skewness for short positions
    out_df['ret'] = np.log(prices.loc[events_['t1'].values].values) - np.log(prices.loc[events_.index])
    out_df['trgt'] = events_['trgt']

    # Meta labeling: Adjust returns based on 'side' if available
    if 'side' in events_:
        out_df['ret'] = out_df['ret'] * events_['side']  # meta-labeling

    # Label events using barrier_touched function
    out_df = barrier_touched(out_df)

    # Meta labeling: Label incorrect events with 'bin' = 0
    if 'side' in events_:
        out_df.loc[out_df['ret'] <= 0, 'bin'] = 0

    # Transform log returns back to normal returns
    out_df['ret'] = np.exp(out_df['ret']) - 1

    # Add 'side' column to the output if present in triple_barrier_events
    tb_cols = triple_barrier_events.columns
    if 'side' in tb_cols:
        out_df['side'] = triple_barrier_events['side']

    return out_df

def bbands(close_prices, window, no_of_stdev):
    # rolling_mean = close_prices.rolling(window=window).mean()
    # rolling_std = close_prices.rolling(window=window).std()
    rolling_mean = close_prices.ewm(span=window).mean()
    rolling_std = close_prices.ewm(span=window).std()

    upper_band = rolling_mean + (rolling_std * no_of_stdev)
    lower_band = rolling_mean - (rolling_std * no_of_stdev)

    return rolling_mean, upper_band, lower_band